import io
import re
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from PIL import Image
from pydantic import BaseModel
from starlette.datastructures import UploadFile

from app.dna_connect.analytics.routes import (
    obter_ip_cliente,
    obter_ou_criar_visitor_id,
    definir_cookie_visitor
)
from app.dna_connect.analytics.service import registrar_evento_analytics
from app.dna_connect.cards.service import (
    resolver_cartao_publico,
    resolver_cartao_visita,
    obter_perfil_cartao_visita_editor,
    salvar_perfil_cartao_visita,
    salvar_foto_cartao_visita,
    remover_foto_cartao_visita,
    obter_foto_cartao_visita,
    salvar_imagem_fundo_cartao_visita,
    remover_imagem_fundo_cartao_visita,
    obter_imagem_fundo_cartao_visita,
    definir_modo_cartao,
    construir_url_publica_cartao,
    gerar_qr_code_cartao,
    obter_vcard_cartao_visita,
    gerar_qr_code_offline_cartao,
    gerar_pdf_cartao_visita,
    salvar_links_cartao_visita,
    gerar_qr_code_pix_cartao,
    obter_payload_pix_cartao,
    salvar_catalogo_cartao_visita,
    obter_imagem_item_catalogo,
    criar_lead_cartao_visita,
    listar_leads_cartao_visita,
    remover_lead_cartao_visita,
    exportar_leads_csv_cartao_visita,
    ativar_cartao,
    atualizar_link_cartao,
    listar_cartoes_por_owner,
    obter_cartao,
    remover_cartao
)
from app.dna_connect.cards.business_profile_repository import CAMPOS_PERFIL
from app.dna_connect.auth.dependencies import get_current_user, get_optional_user

router = APIRouter()

templates = Jinja2Templates(
    directory=[
        str(Path(__file__).resolve().parent / "templates"),
        str(Path(__file__).resolve().parent.parent / "dashboard" / "templates")
    ]
)


def _rastrear_evento_cartao(background_tasks, request, response, card_code, event_type, metadata=None):
    """
    Ponte entre as rotas públicas do cartão e o Analytics (Sprint
    Analytics) — lê/gera o visitor_id, agenda a gravação numa
    BackgroundTask e define o cookie na resposta quando necessário.
    Falhas do Analytics nunca devem derrubar a rota pública (ver
    registrar_evento_analytics/_gravar_evento).
    """

    visitor_id, precisa_definir_cookie = obter_ou_criar_visitor_id(request)

    registrar_evento_analytics(
        background_tasks=background_tasks,
        card_code=card_code,
        event_type=event_type,
        visitor_id=visitor_id,
        ip=obter_ip_cliente(request),
        user_agent=request.headers.get("user-agent"),
        referer=request.headers.get("referer"),
        src_param=request.query_params.get("src"),
        metadata=metadata
    )

    if precisa_definir_cookie:
        definir_cookie_visitor(response, visitor_id)


def _validar_target_url(target_url: str) -> bool:
    """
    Mesma validação usada pela API: URL obrigatória, iniciando com
    http:// ou https://.
    """

    return bool(target_url) and target_url.startswith(("http://", "https://"))


_HEX_COLOR = re.compile(r"#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$")

_COR_FUNDO_PADRAO = "#05070d"
_COR_DESTAQUE_PADRAO = "#3b82f6"


def _cor_fundo_valida(valor):
    """
    Valida que background_color é um hexadecimal seguro para ser
    interpolado num atributo style (#abc ou #aabbcc). Retorna a cor
    padrão da identidade DNA Connect caso ausente ou inválida.
    """

    if valor and _HEX_COLOR.fullmatch(valor.strip()):
        return valor.strip()

    return _COR_FUNDO_PADRAO


def _cor_destaque_valida(valor):
    """
    Mesma validação de _cor_fundo_valida, para accent_color (Sprint 31)
    — cartões sem cor de destaque configurada usam o azul padrão atual.
    """

    if valor and _HEX_COLOR.fullmatch(valor.strip()):
        return valor.strip()

    return _COR_DESTAQUE_PADRAO


_TIPOS_FUNDO_VALIDOS = ("solid", "gradient", "image")
_TIPO_FUNDO_PADRAO = "solid"

_DIRECOES_GRADIENTE = {
    "horizontal": "to right",
    "vertical": "to bottom",
    "diagonal": "to bottom right"
}
_DIRECAO_GRADIENTE_PADRAO = "diagonal"


def _tipo_fundo_valido(valor):
    """
    Cartões existentes nunca tiveram background_type (só
    background_color) — tratar None/valor ausente como 'solid' é o que
    preserva a aparência atual deles sem exigir nenhuma migração de
    dados nem reconfiguração manual.
    """

    if valor in _TIPOS_FUNDO_VALIDOS:
        return valor

    return _TIPO_FUNDO_PADRAO


def _direcao_gradiente_valida(valor):

    if valor in _DIRECOES_GRADIENTE:
        return valor

    return _DIRECAO_GRADIENTE_PADRAO


def _hex_para_rgb(hex_color: str):

    valor = hex_color.lstrip("#")

    if len(valor) == 3:
        valor = "".join(c * 2 for c in valor)

    return tuple(int(valor[i:i + 2], 16) for i in (0, 2, 4))


def _texto_claro_sobre_fundo(hex_color: str) -> bool:
    """
    Heurística simples de luminância (não é um algoritmo completo de
    contraste WCAG) apenas para evitar texto escuro sobre fundo escuro
    ou texto claro sobre fundo muito claro. Reutilizada tanto para o
    fundo do cartão quanto para a cor de destaque (Sprint 31), já que
    o problema (legibilidade do texto sobre uma cor) é o mesmo.
    """

    r, g, b = _hex_para_rgb(hex_color)
    luminancia = (0.299 * r + 0.587 * g + 0.114 * b) / 255

    return luminancia < 0.6


def _luminancia_media_imagem(dados_binarios: bytes) -> float:
    """
    Luminância média aproximada (0 a 1) de uma imagem, usada para
    decidir claro/escuro quando o fundo é uma imagem — mesmo critério
    (limiar 0.6) já usado para cor sólida e gradiente em
    _texto_claro_sobre_fundo, só que aplicado à imagem real em vez de
    assumir sempre texto claro (fotos claras/coloridas, como um fundo
    predominantemente amarelo, ficavam com texto branco ilegível).

    Reduz a imagem a uma miniatura em escala de cinza antes de calcular
    a média — suficiente para estimar o tom geral sem o custo de
    decodificar a imagem em tamanho real a cada acesso à página pública.
    """

    imagem = Image.open(io.BytesIO(dados_binarios)).convert("L")
    imagem.thumbnail((32, 32))

    pixels = list(imagem.getdata())

    if not pixels:
        return 0.0

    return (sum(pixels) / len(pixels)) / 255


def _cor_com_opacidade(hex_color: str, alpha: float) -> str:
    """
    Versão translúcida (rgba) de uma cor hex — usada para os fundos
    suaves dos elementos de destaque (avatar placeholder, badge da
    empresa) quando a cor de destaque é personalizada.
    """

    r, g, b = _hex_para_rgb(hex_color)

    return f"rgba({r}, {g}, {b}, {alpha})"


def _url_segura(valor):
    """
    Aceita URLs http/https (fotos com URL manual, da Sprint 26) ou o
    caminho interno /c/{code}/photo (fotos enviadas por upload, da
    Sprint 28) — nunca outros esquemas, evitando algo como javascript:
    em atributos renderizados.
    """

    if not valor:
        return None

    valor = valor.strip()

    if valor.startswith(("http://", "https://")):
        return valor

    if valor.startswith("/c/"):
        return valor

    return None


def _link_whatsapp(valor):

    if not valor:
        return None

    digitos = re.sub(r"\D", "", valor)

    return f"https://wa.me/{digitos}" if digitos else None


def _link_telefone(valor):

    if not valor:
        return None

    digitos = re.sub(r"[^\d+]", "", valor)

    return f"tel:{digitos}" if digitos else None


def _link_email(valor):

    return f"mailto:{valor.strip()}" if valor else None


def _link_website(valor):

    if not valor:
        return None

    valor = valor.strip()

    return valor if valor.startswith(("http://", "https://")) else f"https://{valor}"


def _link_compartilhar_whatsapp(url_cartao: str) -> str:
    """
    Monta o link "wa.me" para o próprio dono do cartão compartilhar seu
    link por WhatsApp — diferente do botão de contato existente
    (whatsapp_link, onde é o visitante chamando o dono): aqui é o dono
    enviando o próprio cartão pra alguém. Sem número de destino, o
    WhatsApp abre o seletor de contato/conversa do usuário.
    """

    mensagem = f"Confira meu cartão digital DNA Connect: {url_cartao}"

    return f"https://wa.me/?text={quote(mensagem)}"


_EMAIL_SIMPLES = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_CAMPOS_URL_OU_HANDLE = (
    "website",
)


_PALAVRAS_CHAVE_TELEFONE_PIX = ("telefone", "fone", "celular", "phone", "whatsapp")


def _normalizar_chave_pix_telefone(chave: str) -> str:
    """
    Chave Pix do tipo telefone precisa estar no formato internacional
    completo (+55DDDNUMERO, ex: +5548991983553) para os bancos
    reconhecerem — é esse "+55" que diferencia telefone dos outros
    tipos de chave no cadastro do Banco Central (DICT). Sem ele, o
    banco não localiza a chave, mesmo ela estando correta — CPF,
    CNPJ, e-mail e chave aleatória não têm esse problema, por isso
    funcionavam normalmente sem nenhuma formatação.
    """

    digitos = re.sub(r"\D", "", chave)

    if not digitos:
        return chave

    if digitos.startswith("55") and len(digitos) in (12, 13):
        return f"+{digitos}"

    if len(digitos) in (10, 11):
        return f"+55{digitos}"

    return chave


_FORMATOS_FOTO_PERMITIDOS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp"
}

_TAMANHO_MAXIMO_FOTO = 5 * 1024 * 1024  # 5 MB


def _validar_foto(dados_binarios: bytes):
    """
    Valida a foto de perfil no backend, sem confiar no nome do arquivo
    nem no Content-Type declarado pelo navegador: o tamanho é checado
    nos bytes recebidos, e o formato é determinado abrindo a imagem de
    verdade com Pillow (rejeita PDFs, SVGs, GIFs, executáveis
    renomeados ou arquivos corrompidos). Retorna (content_type, erro).
    """

    if len(dados_binarios) > _TAMANHO_MAXIMO_FOTO:
        return None, "A foto deve ter no máximo 5 MB."

    try:

        imagem = Image.open(io.BytesIO(dados_binarios))
        imagem.verify()

    except Exception:

        return None, "Arquivo de foto inválido ou corrompido."

    formato = imagem.format

    if formato not in _FORMATOS_FOTO_PERMITIDOS:

        return None, "Formato de foto não permitido. Envie um arquivo JPG, PNG ou WEBP."

    return _FORMATOS_FOTO_PERMITIDOS[formato], None


def _campo_opcional(form, nome):

    valor = (form.get(nome) or "").strip()

    return valor or None


def _valor_sem_esquema_perigoso(valor):
    """
    Mesma lógica de segurança usada na página pública (Sprint 25): um
    handle normal nunca contém ':'. Se contiver e não for http/https,
    trata-se de um esquema não permitido (ex: javascript:).
    """

    if valor is None:
        return True

    return not (":" in valor and not valor.startswith(("http://", "https://")))


def _validar_dados_perfil(form):
    """
    Extrai e valida os campos do formulário do cartão de visita
    (mesma lista de CAMPOS_PERFIL usada pelo repository, evitando
    duplicar a lista de campos). Validações básicas apenas, conforme
    pedido nesta sprint.
    """

    dados = {campo: _campo_opcional(form, campo) for campo in CAMPOS_PERFIL}
    erros = []

    if dados["pix_key"] and dados["pix_key_type"] and any(
        palavra in dados["pix_key_type"].strip().lower() for palavra in _PALAVRAS_CHAVE_TELEFONE_PIX
    ):
        dados["pix_key"] = _normalizar_chave_pix_telefone(dados["pix_key"])

    if dados["email"] and not _EMAIL_SIMPLES.fullmatch(dados["email"]):
        erros.append("E-mail em formato inválido.")

    if dados["background_color"] and not _HEX_COLOR.fullmatch(dados["background_color"]):
        erros.append("Cor de fundo deve ser um hexadecimal válido (ex: #05070d).")

    if dados["accent_color"] and not _HEX_COLOR.fullmatch(dados["accent_color"]):
        erros.append("Cor de destaque deve ser um hexadecimal válido (ex: #3b82f6).")

    if dados["background_type"] and dados["background_type"] not in _TIPOS_FUNDO_VALIDOS:
        erros.append("Tipo de fundo inválido.")

    if dados["gradient_color_1"] and not _HEX_COLOR.fullmatch(dados["gradient_color_1"]):
        erros.append("Cor 1 do gradiente deve ser um hexadecimal válido (ex: #05070d).")

    if dados["gradient_color_2"] and not _HEX_COLOR.fullmatch(dados["gradient_color_2"]):
        erros.append("Cor 2 do gradiente deve ser um hexadecimal válido (ex: #0a47ff).")

    if dados["gradient_direction"] and dados["gradient_direction"] not in _DIRECOES_GRADIENTE:
        erros.append("Direção do gradiente inválida.")

    if dados["google_maps_url"] and not dados["google_maps_url"].startswith(("http://", "https://")):
        erros.append("O link do Google Maps deve ser uma URL válida, iniciando com http:// ou https://.")

    # Limites exigidos pelo próprio padrão de QR Code Pix do Banco
    # Central (BR Code) para os campos de nome/cidade do beneficiário —
    # não são um capricho da interface, um valor maior quebraria o
    # payload gerado em construir_payload_pix.
    if dados["pix_beneficiary_name"] and len(dados["pix_beneficiary_name"]) > 25:
        erros.append("Nome do beneficiário Pix deve ter no máximo 25 caracteres.")

    if dados["pix_beneficiary_city"] and len(dados["pix_beneficiary_city"]) > 15:
        erros.append("Cidade do beneficiário Pix deve ter no máximo 15 caracteres.")

    for campo in _CAMPOS_URL_OU_HANDLE:

        if not _valor_sem_esquema_perigoso(dados[campo]):
            erros.append(f"O campo {campo} contém um endereço não permitido.")

    return dados, erros


_ICONES_LINK_VALIDOS = ("instagram", "linkedin", "facebook", "tiktok", "youtube", "link")
_LABEL_LINK_TAMANHO_MAXIMO = 40


def _validar_links(form):
    """
    Extrai e valida a lista de links livres do formulário (Sprint 4 —
    substitui os antigos campos fixos de Instagram/LinkedIn/Facebook/
    TikTok/YouTube por uma lista de tamanho arbitrário). Cada link vem
    como uma linha de 3 campos (link_label[], link_url[], link_icon[])
    com o mesmo índice — o navegador manda um trio por link adicionado.

    Linhas totalmente vazias são ignoradas (permite "remover" uma linha
    no navegador só esvaziando os campos, sem precisar reindexar nada).
    """

    rotulos = form.getlist("link_label[]")
    urls = form.getlist("link_url[]")
    icones = form.getlist("link_icon[]")

    links = []
    erros = []

    for rotulo, url, icone in zip(rotulos, urls, icones):

        rotulo = (rotulo or "").strip()
        url = (url or "").strip()
        icone = (icone or "link").strip()

        if not rotulo and not url:
            continue

        if not rotulo:
            erros.append("Todo link precisa de um rótulo.")
            continue

        if len(rotulo) > _LABEL_LINK_TAMANHO_MAXIMO:
            erros.append(f'O rótulo "{rotulo}" deve ter no máximo {_LABEL_LINK_TAMANHO_MAXIMO} caracteres.')
            continue

        if not url:
            erros.append(f'O link "{rotulo}" precisa de uma URL.')
            continue

        if not _valor_sem_esquema_perigoso(url):
            erros.append(f'O link "{rotulo}" contém um endereço não permitido.')
            continue

        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        if icone not in _ICONES_LINK_VALIDOS:
            icone = "link"

        links.append({"label": rotulo, "url": url, "icon": icone})

    return links, erros


_TAMANHO_MAXIMO_TITULO_CATALOGO = 60


async def _validar_catalogo(form):
    """
    Extrai e valida os itens do catálogo de produtos/serviços (Sprint
    6). Cada item chega como um conjunto de campos catalog_*[] no
    mesmo índice — mesmo padrão de listas paralelas já usado pelos
    links livres (_validar_links), com um campo a mais (imagem, por
    item). Linhas sem título são ignoradas (permite "remover" uma
    linha no navegador só limpando o título).

    `id` (catalog_id[]) identifica um item já existente, para
    salvar_catalogo_cartao_visita decidir entre atualizar ou criar —
    ver a função para o motivo de não ser um "apagar tudo e recriar"
    como a lista de links.
    """

    ids = form.getlist("catalog_id[]")
    titulos = form.getlist("catalog_title[]")
    descricoes = form.getlist("catalog_description[]")
    precos = form.getlist("catalog_price[]")
    rotulos_acao = form.getlist("catalog_action_label[]")
    urls_acao = form.getlist("catalog_action_url[]")
    arquivos_imagem = form.getlist("catalog_image[]")

    itens = []
    erros = []

    for i in range(len(titulos)):

        titulo = (titulos[i] or "").strip()

        if not titulo:
            continue

        if len(titulo) > _TAMANHO_MAXIMO_TITULO_CATALOGO:
            erros.append(f'O título "{titulo}" deve ter no máximo {_TAMANHO_MAXIMO_TITULO_CATALOGO} caracteres.')
            continue

        descricao = (descricoes[i].strip() if i < len(descricoes) and descricoes[i] else None) or None
        preco = (precos[i].strip() if i < len(precos) and precos[i] else None) or None
        rotulo_acao = (rotulos_acao[i].strip() if i < len(rotulos_acao) and rotulos_acao[i] else None) or None
        url_acao = urls_acao[i].strip() if i < len(urls_acao) and urls_acao[i] else ""

        if url_acao and not url_acao.startswith(("http://", "https://")):
            url_acao = f"https://{url_acao}"

        if url_acao and not _valor_sem_esquema_perigoso(url_acao):
            erros.append(f'O link do item "{titulo}" contém um endereço não permitido.')
            continue

        item_id_str = (ids[i] if i < len(ids) else "").strip()
        item_id = int(item_id_str) if item_id_str.isdigit() else None

        imagem_bytes = None
        imagem_content_type = None

        arquivo = arquivos_imagem[i] if i < len(arquivos_imagem) else None

        if isinstance(arquivo, UploadFile) and arquivo.filename:

            conteudo = await arquivo.read()
            imagem_content_type, erro_imagem = _validar_foto(conteudo)

            if erro_imagem:
                erros.append(f'Imagem do item "{titulo}": {erro_imagem}')
                continue

            imagem_bytes = conteudo

        itens.append({
            "id": item_id,
            "title": titulo,
            "description": descricao,
            "price": preco,
            "action_label": rotulo_acao,
            "action_url": url_acao or None,
            "imagem_bytes": imagem_bytes,
            "imagem_content_type": imagem_content_type,
            # Usado só para repopular a prévia na re-renderização em
            # caso de erro (ver _renderizar_pagina_edicao) — a imagem
            # de um item existente que não recebeu arquivo novo neste
            # envio simplesmente não aparece até o formulário ser
            # salvo com sucesso, para não complicar essa validação
            # buscando o estado atual no banco.
            "tem_imagem": imagem_bytes is not None
        })

    return itens, erros


_TAMANHO_MAXIMO_MENSAGEM_LEAD = 1000


def _validar_lead(form):
    """
    Extrai e valida o formulário de contato da página pública (Sprint
    7). Nome é obrigatório; e-mail e telefone são opcionais, mas pelo
    menos um dos dois precisa estar preenchido — sem nenhuma forma de
    contato, o lead não serve pra nada.
    """

    dados = {
        "name": (form.get("name") or "").strip(),
        "email": (form.get("email") or "").strip() or None,
        "phone": (form.get("phone") or "").strip() or None,
        "message": (form.get("message") or "").strip() or None
    }

    erros = []

    if not dados["name"]:
        erros.append("Nome é obrigatório.")

    if not dados["email"] and not dados["phone"]:
        erros.append("Informe pelo menos um e-mail ou telefone para contato.")

    if dados["email"] and not _EMAIL_SIMPLES.fullmatch(dados["email"]):
        erros.append("E-mail em formato inválido.")

    if dados["message"] and len(dados["message"]) > _TAMANHO_MAXIMO_MENSAGEM_LEAD:
        erros.append(f"A mensagem deve ter no máximo {_TAMANHO_MAXIMO_MENSAGEM_LEAD} caracteres.")

    return dados, erros


class ActivateRequest(BaseModel):

    card_code: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "card_code": "TESTE01"
            }
        }
    }


class UpdateCardRequest(BaseModel):

    target_url: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "target_url": "https://instagram.com/denian_df"
            }
        }
    }


@router.get("/c/{card_code}")
def redirect_card(card_code: str, request: Request, background_tasks: BackgroundTasks, src: str = None):
    """
    Resolve o acesso público de um cartão NFC/QR Code pelo código —
    mesmo endereço físico impresso/gravado para os dois modos.

    - Não existe: 404.
    - mode=business_card: redireciona (307) para /c/{code}/cartao-visita,
      já que o NFC/QR físico só conhece este endereço — o ?src= é
      encaminhado para lá, que é quem de fato registra o page_view
      (evita contar a mesma visita duas vezes).
    - custom_link, mas ainda não está configurado: página pública
      informativa (conta como page_view aqui mesmo).
    - custom_link e está configurado: redireciona (307) para o
      target_url (conta como page_view aqui; o ?src= não é
      encaminhado para o site externo, é só para uso interno).
    """

    resultado = resolver_cartao_publico(card_code)

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "business_card":

        destino = f"/c/{card_code}/cartao-visita"

        if src:
            destino += f"?src={quote(src)}"

        return RedirectResponse(url=destino, status_code=307)

    if resultado["status"] == "unconfigured":

        resposta = templates.TemplateResponse(
            request=request,
            name="card_unconfigured.html",
            context={}
        )

        _rastrear_evento_cartao(background_tasks, request, resposta, card_code, "page_view")

        return resposta

    resposta = RedirectResponse(url=resultado["target_url"], status_code=307)

    _rastrear_evento_cartao(background_tasks, request, resposta, card_code, "page_view")

    return resposta


@router.get("/c/{card_code}/cartao-visita")
def card_business_profile(
    card_code: str,
    request: Request,
    background_tasks: BackgroundTasks,
    lead: str = None,
    erro_lead: str = None,
    src: str = None
):
    """
    Página pública do cartão de visita digital (mode=business_card).

    - Cartão inexistente: 404.
    - Cartão existente mas em outro modo (custom_link): 404 (coerente com
      o restante do módulo — o cartão não representa um cartão de visita).
    - Cartão em modo business_card sem perfil preenchido: página de
      "ainda não configurado" (200, nunca 500).
    - Cartão em modo business_card com perfil: renderiza a página HTML,
      expondo apenas os campos públicos do perfil (nunca id, card_id,
      owner_id ou timestamps).

    `lead`/`erro_lead` (query string) vêm do redirecionamento após o
    envio do formulário de contato (POST /c/{card_code}/leads) — sem
    eles, a página normal não passa nenhum dos dois.
    """

    resultado = resolver_cartao_visita(card_code)

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "wrong_mode":

        raise HTTPException(
            status_code=404,
            detail="Este cartão não está configurado como cartão de visita digital."
        )

    perfil = resultado["profile"]

    if not perfil:

        resposta_pendente = templates.TemplateResponse(
            request=request,
            name="business_card_pending.html",
            context={}
        )

        _rastrear_evento_cartao(background_tasks, request, resposta_pendente, card_code, "page_view")

        return resposta_pendente

    tipo_fundo = _tipo_fundo_valido(perfil.background_type)

    if tipo_fundo == "gradient" and perfil.gradient_color_1 and perfil.gradient_color_2:

        cor1 = _cor_fundo_valida(perfil.gradient_color_1)
        cor2 = _cor_fundo_valida(perfil.gradient_color_2)
        direcao_css = _DIRECOES_GRADIENTE[_direcao_gradiente_valida(perfil.gradient_direction)]

        estilo_fundo = f"background-image: linear-gradient({direcao_css}, {cor1}, {cor2});"
        texto_claro = _texto_claro_sobre_fundo(cor1) and _texto_claro_sobre_fundo(cor2)

    elif tipo_fundo == "image" and perfil.background_image:

        # Sem aspas de propósito: url_imagem é sempre um caminho interno
        # controlado (/c/{code}/background-image, nunca digitado pelo
        # usuário), então dispensa aspas em CSS — e evita depender do
        # autoescape do Jinja (que trocaria ' por &#39; no HTML e só
        # funcionaria por o navegador decodificar a entidade de volta).
        url_imagem = _url_segura(perfil.background_image)
        estilo_fundo = f"background-image: url({url_imagem}); background-size: cover; background-position: center; background-repeat: no-repeat;"

        imagem_fundo = obter_imagem_fundo_cartao_visita(card_code)
        # Se por algum motivo os bytes não puderem ser lidos (nunca deveria
        # acontecer, já que perfil.background_image só existe quando há
        # imagem salva), texto claro continua sendo o fallback mais seguro.
        texto_claro = _luminancia_media_imagem(imagem_fundo["dados"]) < 0.6 if imagem_fundo else True

    else:

        # solid (ou gradient/image escolhidos mas ainda sem cores/imagem
        # salvas) caem aqui — mesmo comportamento de sempre.
        cor_fundo = _cor_fundo_valida(perfil.background_color)
        estilo_fundo = f"background-color: {cor_fundo};"
        texto_claro = _texto_claro_sobre_fundo(cor_fundo)

    cor_destaque = _cor_destaque_valida(perfil.accent_color)

    resposta = templates.TemplateResponse(
        request=request,
        name="business_card.html",
        context={
            "card_code": card_code,
            "nome": perfil.name,
            "cargo": perfil.professional_title,
            "empresa": perfil.company,
            "foto": _url_segura(perfil.profile_photo),
            "bio": perfil.bio,
            "whatsapp_link": _link_whatsapp(perfil.whatsapp),
            "telefone_link": _link_telefone(perfil.phone),
            "email_link": _link_email(perfil.email),
            "links": resultado["links"],
            "catalogo": resultado["catalogo"],
            "website_link": _link_website(perfil.website),
            "google_maps_link": _url_segura(perfil.google_maps_url),
            "pix_key": perfil.pix_key,
            "pix_key_type": perfil.pix_key_type,
            "pix_cobranca_disponivel": bool(
                perfil.pix_key and perfil.pix_beneficiary_name and perfil.pix_beneficiary_city
            ),
            "estilo_fundo": estilo_fundo,
            "texto_claro": texto_claro,
            "cor_destaque": cor_destaque,
            "cor_destaque_soft": _cor_com_opacidade(cor_destaque, 0.16),
            "cor_destaque_texto": "#ffffff" if _texto_claro_sobre_fundo(cor_destaque) else "#111827",
            "lead_enviado": lead == "enviado",
            "erro_lead": erro_lead
        }
    )

    _rastrear_evento_cartao(background_tasks, request, resposta, card_code, "page_view")

    return resposta


@router.post("/c/{card_code}/leads")
async def submit_lead(card_code: str, request: Request, background_tasks: BackgroundTasks):
    """
    Recebe o formulário de contato/lead da página pública (Sprint 7).
    Rota pública, sem autenticação — qualquer visitante pode deixar seu
    contato. Redireciona de volta para a própria página pública, com
    um indicador de sucesso/erro na query string (não há sessão nem
    dado sensível para justificar POST-redirect com corpo).

    O evento lead_form_submit registrado no Analytics (Sprint Analytics)
    mede só a interação (que um lead foi enviado) — os dados pessoais
    preenchidos no formulário continuam exclusivamente em card_leads,
    nunca em analytics_events.
    """

    form = await request.form()
    dados, erros = _validar_lead(form)

    if erros:
        return RedirectResponse(
            url=f"/c/{card_code}/cartao-visita?erro_lead={quote(' '.join(erros))}",
            status_code=302
        )

    resultado = criar_lead_cartao_visita(card_code, dados)

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    resposta = RedirectResponse(url=f"/c/{card_code}/cartao-visita?lead=enviado", status_code=302)

    _rastrear_evento_cartao(background_tasks, request, resposta, card_code, "lead_form_submit")

    return resposta


@router.get("/c/{card_code}/photo")
def card_business_photo(card_code: str):
    """
    Serve os bytes da foto de perfil enviada por upload (Sprint 28).
    Rota pública (sem autenticação) — a foto é exibida na página
    pública do cartão de visita, mesmo nível de exposição de qualquer
    outro dado ali. 404 se o cartão não existir ou não houver foto.
    """

    foto = obter_foto_cartao_visita(card_code)

    if not foto:
        raise HTTPException(status_code=404, detail="Foto não encontrada.")

    return Response(content=foto["dados"], media_type=foto["content_type"])


@router.get("/c/{card_code}/background-image")
def card_business_background_image(card_code: str):
    """
    Serve os bytes da imagem de fundo (background_type = image)
    enviada por upload. Mesmo nível de exposição/rota pública de
    card_business_photo, para a segunda imagem opcional do perfil.
    """

    imagem = obter_imagem_fundo_cartao_visita(card_code)

    if not imagem:
        raise HTTPException(status_code=404, detail="Imagem de fundo não encontrada.")

    return Response(content=imagem["dados"], media_type=imagem["content_type"])


@router.get("/c/{card_code}/catalog/{item_id}/image")
def card_catalog_item_image(card_code: str, item_id: int):
    """
    Serve os bytes da foto de um item do catálogo (Sprint 6). Rota
    pública, sem autenticação — mesmo nível de exposição das demais
    imagens do perfil (foto, fundo). O card_code na URL é só para
    manter o padrão de rota já usado pelas outras imagens; quem
    resolve a imagem é o item_id.
    """

    imagem = obter_imagem_item_catalogo(item_id)

    if not imagem:
        raise HTTPException(status_code=404, detail="Imagem não encontrada.")

    return Response(content=imagem["dados"], media_type=imagem["content_type"])


@router.get("/c/{card_code}/vcard")
def card_business_vcard(card_code: str, request: Request, background_tasks: BackgroundTasks):
    """
    Serve o vCard do cartão de visita para download ("Salvar contato"
    na página pública) — mesma fonte de dados usada pelo QR Code
    offline. Rota pública, sem autenticação: é o mesmo nível de
    exposição do restante do perfil na página pública. 404 se o cartão
    não existir, não estiver em modo business_card, ou não tiver perfil
    preenchido ainda.
    """

    vcard = obter_vcard_cartao_visita(card_code)

    if not vcard:
        raise HTTPException(status_code=404, detail="Cartão de visita não encontrado.")

    resposta = Response(
        content=vcard,
        media_type="text/vcard",
        headers={
            "Content-Disposition": f'attachment; filename="{card_code}.vcf"'
        }
    )

    _rastrear_evento_cartao(background_tasks, request, resposta, card_code, "vcard_download")

    return resposta


@router.get("/c/{card_code}/pdf")
def card_business_pdf(card_code: str):
    """
    Serve o PDF do cartão de visita digital, para download/anexo em
    e-mail ou WhatsApp. Rota pública, sem autenticação — mesmo nível de
    exposição do restante do perfil. 404 nas mesmas condições do
    vCard/QR offline (cartão inexistente, modo custom_link, ou sem
    perfil preenchido).
    """

    pdf_bytes = gerar_pdf_cartao_visita(card_code)

    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="Cartão de visita não encontrado.")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{card_code}.pdf"'
        }
    )


def _valor_pix_da_query(valor_str):
    """
    Converte o valor digitado pelo pagador (query string, aceita
    vírgula ou ponto decimal) para float — retorna None se estiver
    ausente, inválido ou não positivo, caso em que o QR Code é gerado
    sem valor pré-preenchido (o pagador digita no próprio app do banco).
    """

    if not valor_str:
        return None

    try:
        valor = float(valor_str.strip().replace(",", "."))
    except ValueError:
        return None

    return valor if valor > 0 else None


@router.get("/c/{card_code}/pix-qr")
def card_pix_qr(card_code: str, request: Request, background_tasks: BackgroundTasks, valor: str = None):
    """
    Gera o QR Code de cobrança Pix (padrão BR Code do Banco Central) do
    cartão, com o valor informado pelo pagador no momento (opcional).
    Rota pública, sem autenticação — mesmo nível de exposição da chave
    Pix já exibida na própria página. Não confirma pagamento, só gera
    o código (ver obter_payload_pix_cartao).
    """

    imagem_png = gerar_qr_code_pix_cartao(card_code, valor=_valor_pix_da_query(valor))

    if imagem_png is None:
        raise HTTPException(status_code=404, detail="Cobrança Pix não disponível para este cartão.")

    resposta = Response(content=imagem_png, media_type="image/png")

    _rastrear_evento_cartao(background_tasks, request, resposta, card_code, "pix_qr_generate")

    return resposta


@router.get("/c/{card_code}/pix-copia-e-cola")
def card_pix_copia_cola(card_code: str, valor: str = None):
    """
    Retorna o código Pix "copia e cola" (o mesmo payload codificado no
    QR Code, como texto puro) — usado quando quem vai pagar está no
    mesmo aparelho que exibe o cartão (não dá pra escanear a própria
    tela).
    """

    payload = obter_payload_pix_cartao(card_code, valor=_valor_pix_da_query(valor))

    if payload is None:
        raise HTTPException(status_code=404, detail="Cobrança Pix não disponível para este cartão.")

    return Response(content=payload, media_type="text/plain")


@router.post("/activate")
def activate_card(
    payload: ActivateRequest,
    current_user=Depends(get_current_user)
):
    """
    Ativa um cartão, associando-o ao usuário autenticado.
    """

    resultado = ativar_cartao(
        email=current_user.email,
        card_code=payload.card_code
    )

    if resultado["status"] == "unauthorized":

        raise HTTPException(
            status_code=401,
            detail="Usuário não encontrado. Cadastre-se em /register antes de ativar um cartão."
        )

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "already_activated":

        raise HTTPException(
            status_code=409,
            detail="Este cartão já está ativado."
        )

    user = resultado["user"]

    return {
        "message": "Cartão ativado com sucesso!",
        "card_code": resultado["card_code"],
        "owner": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }


@router.get("/cards")
def list_my_cards(current_user=Depends(get_current_user)):
    """
    Lista os cartões pertencentes ao usuário autenticado.
    """

    cartoes = listar_cartoes_por_owner(current_user.id)

    return [
        {
            "code": card.code,
            "target_url": card.target_url,
            "activated": card.activated,
            "created_at": card.created_at,
            "updated_at": card.updated_at
        }
        for card in cartoes
    ]


@router.get("/cards/activate")
def activate_card_view(
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Renderiza a tela web de ativação de cartão.
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="activate_card.html",
        context={"erro": None}
    )


@router.post("/cards/activate")
async def activate_card_submit(
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Processa a ativação web de um cartão, reutilizando exatamente o
    mesmo Service de ativação usado pela API (POST /activate).
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    form = await request.form()
    card_code = form.get("card_code", "")

    resultado = ativar_cartao(
        email=current_user.email,
        card_code=card_code
    )

    if resultado["status"] == "unauthorized":

        return templates.TemplateResponse(
            request=request,
            name="activate_card.html",
            context={
                "erro": "Usuário não encontrado. Cadastre-se em /register antes de ativar um cartão."
            },
            status_code=401
        )

    if resultado["status"] == "not_found":

        return templates.TemplateResponse(
            request=request,
            name="activate_card.html",
            context={"erro": "Cartão não encontrado."},
            status_code=404
        )

    if resultado["status"] == "already_activated":

        return templates.TemplateResponse(
            request=request,
            name="activate_card.html",
            context={"erro": "Este cartão já está ativado."},
            status_code=409
        )

    return RedirectResponse(url="/dashboard/view", status_code=302)


@router.get("/cards/{card_code}")
def get_card(
    card_code: str,
    current_user=Depends(get_current_user)
):
    """
    Retorna os detalhes de um cartão pertencente ao usuário autenticado.
    """

    resultado = obter_cartao(
        card_code=card_code,
        owner_id=current_user.id
    )

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para visualizar este cartão."
        )

    card = resultado["card"]

    return {
        "code": card.code,
        "target_url": card.target_url,
        "activated": card.activated,
        "created_at": card.created_at,
        "updated_at": card.updated_at
    }


@router.put("/cards/{card_code}")
def update_card(
    card_code: str,
    payload: UpdateCardRequest,
    current_user=Depends(get_current_user)
):
    """
    Atualiza o link (target_url) de um cartão pertencente ao usuário autenticado.
    """

    if not _validar_target_url(payload.target_url):

        raise HTTPException(
            status_code=400,
            detail="target_url deve ser uma URL válida, iniciando com http:// ou https://."
        )

    resultado = atualizar_link_cartao(
        card_code=card_code,
        owner_id=current_user.id,
        target_url=payload.target_url
    )

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para editar este cartão."
        )

    return {
        "message": "Link do cartão atualizado com sucesso!",
        "card_code": resultado["card_code"],
        "target_url": resultado["target_url"]
    }


@router.get("/cards/{card_code}/qr")
def card_qr_owner(
    card_code: str,
    current_user=Depends(get_optional_user)
):
    """
    Retorna o PNG do QR Code do cartão para o próprio proprietário
    (Sprint 29) — mesma imagem gerada por gerar_qr_code_cartao (Sprint
    23, já usada pela rota administrativa), só que autorizada por posse
    do cartão em vez de por papel de admin. Usado tanto para exibir o
    QR inline no editor quanto para download.
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    resultado = obter_cartao(card_code=card_code, owner_id=current_user.id)

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para acessar este cartão."
        )

    imagem_png = gerar_qr_code_cartao(card_code)

    return Response(
        content=imagem_png,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="dna-connect-{card_code}-qr.png"'
        }
    )


@router.get("/cards/{card_code}/qr-offline")
def card_qr_offline_owner(
    card_code: str,
    current_user=Depends(get_optional_user)
):
    """
    QR Code offline (vCard) do cartão, para o próprio proprietário —
    mesma autorização de card_qr_owner, só que o conteúdo codificado é
    um vCard em vez do link público. Só existe para cartões em modo
    business_card com perfil preenchido (ver gerar_qr_code_offline_cartao).
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    resultado = obter_cartao(card_code=card_code, owner_id=current_user.id)

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para acessar este cartão."
        )

    imagem_png = gerar_qr_code_offline_cartao(card_code)

    if imagem_png is None:

        raise HTTPException(
            status_code=404,
            detail="QR Code offline disponível apenas para cartões em modo Cartão de visita, com o perfil preenchido."
        )

    return Response(
        content=imagem_png,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="dna-connect-{card_code}-qr-offline.png"'
        }
    )


def _renderizar_pagina_edicao(
    request: Request,
    card_code: str,
    current_user,
    erro=None,
    sucesso=None,
    dados_pendentes=None,
    links_pendentes=None,
    catalogo_pendente=None,
    status_code=200
):
    """
    Monta o contexto completo da tela de edição (cartão + modo +
    perfil de cartão de visita), reaproveitado tanto pelo GET quanto
    pelos POSTs desta seção quando precisam re-renderizar a página
    (com erro, ou repopulando dados ainda não salvos).
    """

    resultado = obter_perfil_cartao_visita_editor(card_code, owner_id=current_user.id)

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para editar este cartão."
        )

    cartao = resultado["card"]
    perfil_real = resultado["profile"]
    perfil = dados_pendentes if dados_pendentes is not None else perfil_real
    links = links_pendentes if links_pendentes is not None else resultado["links"]
    catalogo = catalogo_pendente if catalogo_pendente is not None else resultado["catalogo"]
    # foto_atual/fundo_imagem_atual refletem sempre o que está de fato
    # salvo no banco, nunca o dict de dados pendentes (que não inclui
    # essas imagens — ver save_business_profile)
    foto_atual = _url_segura(perfil_real.profile_photo) if perfil_real else None
    fundo_imagem_atual = _url_segura(perfil_real.background_image) if perfil_real else None
    url_cartao_fisico = construir_url_publica_cartao(cartao.code)

    return templates.TemplateResponse(
        request=request,
        name="edit_card.html",
        context={
            "cartao": cartao,
            "perfil": perfil,
            "links": links,
            "catalogo": catalogo,
            "foto_atual": foto_atual,
            "fundo_imagem_atual": fundo_imagem_atual,
            "url_cartao_fisico": url_cartao_fisico,
            "url_qr_cartao": f"/cards/{cartao.code}/qr",
            "url_qr_offline_cartao": f"/cards/{cartao.code}/qr-offline",
            "url_compartilhar_whatsapp": _link_compartilhar_whatsapp(url_cartao_fisico),
            "url_pdf_cartao": f"/c/{cartao.code}/pdf",
            "erro": erro,
            "sucesso": sucesso
        },
        status_code=status_code
    )


@router.get("/cards/{card_code}/edit")
def edit_card_view(
    card_code: str,
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Renderiza a tela web de edição do cartão: seleção de modo e, de
    acordo com o modo atual, o formulário de link personalizado ou o
    formulário/preview do cartão de visita digital.
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    return _renderizar_pagina_edicao(request, card_code, current_user)


@router.post("/cards/{card_code}/edit")
async def edit_card_submit(
    card_code: str,
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Processa a edição web do link do cartão, reutilizando exatamente o
    mesmo Service de atualização usado pela API (PUT /cards/{card_code}).
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    form = await request.form()
    target_url = form.get("target_url", "")

    if not _validar_target_url(target_url):

        return _renderizar_pagina_edicao(
            request,
            card_code,
            current_user,
            erro="target_url deve ser uma URL válida, iniciando com http:// ou https://.",
            status_code=400
        )

    resultado = atualizar_link_cartao(
        card_code=card_code,
        owner_id=current_user.id,
        target_url=target_url
    )

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para editar este cartão."
        )

    return RedirectResponse(url="/dashboard/view", status_code=302)


@router.post("/cards/{card_code}/mode")
async def set_card_mode(
    card_code: str,
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Alterna o modo do cartão (custom_link <-> business_card). Nunca
    apaga target_url nem os dados do perfil de cartão de visita — ambos
    permanecem armazenados; apenas o modo ativo muda o que é exibido
    publicamente (regra definida na Sprint 24). Reaproveita
    definir_modo_cartao, que já valida a posse do cartão.
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    form = await request.form()
    mode = form.get("mode", "")

    resultado = definir_modo_cartao(card_code, owner_id=current_user.id, mode=mode)

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para editar este cartão."
        )

    if resultado["status"] == "invalid_mode":

        return _renderizar_pagina_edicao(
            request,
            card_code,
            current_user,
            erro="Modo inválido.",
            status_code=400
        )

    return RedirectResponse(url=f"/cards/{card_code}/edit", status_code=302)


@router.post("/cards/{card_code}/business-profile")
async def save_business_profile(
    card_code: str,
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Salva os dados do cartão de visita digital e garante que o modo do
    cartão fique como business_card (mesmo que o proprietário esteja
    apenas revisitando um cartão que já estava nesse modo). Reaproveita
    salvar_perfil_cartao_visita e definir_modo_cartao (Sprint 24), sem
    duplicar nenhuma lógica de persistência ou de posse do cartão.

    Se uma foto for enviada junto (campo profile_photo_file, formulário
    multipart), ela é validada e salva (Sprint 28). Se nenhum arquivo
    for enviado, a foto atual (se houver) permanece intocada — salvar
    o restante do perfil nunca apaga a foto.
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    form = await request.form()
    dados, erros = _validar_dados_perfil(form)
    links, erros_links = _validar_links(form)
    erros.extend(erros_links)

    conteudo_foto = None
    content_type_foto = None

    arquivo_foto = form.get("profile_photo_file")

    if isinstance(arquivo_foto, UploadFile) and arquivo_foto.filename:

        conteudo_foto = await arquivo_foto.read()
        content_type_foto, erro_foto = _validar_foto(conteudo_foto)

        if erro_foto:
            erros.append(erro_foto)

    conteudo_fundo = None
    content_type_fundo = None

    arquivo_fundo = form.get("background_image_file")

    if isinstance(arquivo_fundo, UploadFile) and arquivo_fundo.filename:

        conteudo_fundo = await arquivo_fundo.read()
        content_type_fundo, erro_fundo = _validar_foto(conteudo_fundo)

        if erro_fundo:
            erros.append(erro_fundo)

    if erros:

        return _renderizar_pagina_edicao(
            request,
            card_code,
            current_user,
            erro=" ".join(erros),
            dados_pendentes=dados,
            links_pendentes=links,
            status_code=400
        )

    resultado = salvar_perfil_cartao_visita(card_code, owner_id=current_user.id, dados=dados)

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para editar este cartão."
        )

    if conteudo_foto is not None:

        salvar_foto_cartao_visita(
            card_code,
            owner_id=current_user.id,
            dados_binarios=conteudo_foto,
            content_type=content_type_foto
        )

    if conteudo_fundo is not None:

        salvar_imagem_fundo_cartao_visita(
            card_code,
            owner_id=current_user.id,
            dados_binarios=conteudo_fundo,
            content_type=content_type_fundo
        )

    salvar_links_cartao_visita(card_code, owner_id=current_user.id, links=links)

    definir_modo_cartao(card_code, owner_id=current_user.id, mode="business_card")

    return RedirectResponse(url=f"/cards/{card_code}/edit", status_code=302)


@router.post("/cards/{card_code}/catalog")
async def save_catalog(
    card_code: str,
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Salva o catálogo de produtos/serviços do cartão (Sprint 6). Rota
    própria, separada de save_business_profile: cada item pode ter sua
    própria foto, e misturar isso no formulário principal do perfil
    complicaria a lógica de "manter foto atual se nenhum arquivo novo
    for enviado" sem ganho nenhum (ver salvar_catalogo_cartao_visita).
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    form = await request.form()
    itens, erros = await _validar_catalogo(form)

    if erros:

        return _renderizar_pagina_edicao(
            request,
            card_code,
            current_user,
            erro=" ".join(erros),
            catalogo_pendente=itens,
            status_code=400
        )

    resultado = salvar_catalogo_cartao_visita(card_code, owner_id=current_user.id, itens=itens)

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para editar este cartão."
        )

    return RedirectResponse(url=f"/cards/{card_code}/edit", status_code=302)


@router.post("/cards/{card_code}/business-profile/photo/remove")
async def remove_business_profile_photo(
    card_code: str,
    current_user=Depends(get_optional_user)
):
    """
    Remove a foto de perfil do cartão de visita (Sprint 28). Não afeta
    os demais campos do perfil nem o modo do cartão.
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    resultado = remover_foto_cartao_visita(card_code, owner_id=current_user.id)

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para editar este cartão."
        )

    return RedirectResponse(url=f"/cards/{card_code}/edit", status_code=302)


@router.post("/cards/{card_code}/business-profile/background-image/remove")
async def remove_business_profile_background_image(
    card_code: str,
    current_user=Depends(get_optional_user)
):
    """
    Remove a imagem de fundo do cartão de visita. Não afeta os demais
    campos do perfil, o modo do cartão nem o background_type salvo —
    mesmo padrão de remove_business_profile_photo.
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    resultado = remover_imagem_fundo_cartao_visita(card_code, owner_id=current_user.id)

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para editar este cartão."
        )

    return RedirectResponse(url=f"/cards/{card_code}/edit", status_code=302)


@router.post("/cards/{card_code}/remove")
def remove_card(
    card_code: str,
    current_user=Depends(get_optional_user)
):
    """
    Remove a associação do cartão com o usuário autenticado (remoção
    lógica, reutilizando exatamente o Service de remoção).
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    resultado = remover_cartao(
        card_code=card_code,
        owner_id=current_user.id
    )

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para remover este cartão."
        )

    return RedirectResponse(url="/dashboard/view", status_code=302)


@router.get("/cards/{card_code}/leads")
def view_leads(
    card_code: str,
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Lista os leads recebidos pelo cartão (Sprint 7) — só o dono
    autenticado pode ver.
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    resultado = listar_leads_cartao_visita(card_code, owner_id=current_user.id)

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para ver os leads deste cartão."
        )

    return templates.TemplateResponse(
        request=request,
        name="leads.html",
        context={"cartao": resultado["card"], "leads": resultado["leads"]}
    )


@router.get("/cards/{card_code}/leads/export")
def export_leads(
    card_code: str,
    current_user=Depends(get_optional_user)
):
    """
    Baixa os leads do cartão em CSV — mesma checagem de posse de
    view_leads.
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    resultado = exportar_leads_csv_cartao_visita(card_code, owner_id=current_user.id)

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para exportar os leads deste cartão."
        )

    return Response(
        content=resultado["csv"],
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="leads-{card_code}.csv"'
        }
    )


@router.post("/cards/{card_code}/leads/{lead_id}/delete")
def delete_lead(
    card_code: str,
    lead_id: int,
    current_user=Depends(get_optional_user)
):
    """
    Remove um lead — mesma checagem de posse de view_leads, mais a
    checagem de que o lead pertence mesmo a este cartão (ver
    remover_lead_cartao_visita).
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    resultado = remover_lead_cartao_visita(card_code, owner_id=current_user.id, lead_id=lead_id)

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Lead não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para remover leads deste cartão."
        )

    return RedirectResponse(url=f"/cards/{card_code}/leads", status_code=302)
