import io
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from PIL import Image
from pydantic import BaseModel
from starlette.datastructures import UploadFile

from app.dna_connect.cards.service import (
    resolver_cartao_publico,
    resolver_cartao_visita,
    obter_perfil_cartao_visita_editor,
    salvar_perfil_cartao_visita,
    salvar_foto_cartao_visita,
    remover_foto_cartao_visita,
    obter_foto_cartao_visita,
    definir_modo_cartao,
    construir_url_publica_cartao,
    gerar_qr_code_cartao,
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


def _url_rede_social(base_url: str, valor):
    """
    Se o valor já for uma URL http/https, usa como está. Caso contrário,
    trata como um @handle e monta a URL do perfil na rede social.
    """

    if not valor:
        return None

    valor = valor.strip()

    if valor.startswith(("http://", "https://")):
        return valor

    return f"{base_url}{valor.lstrip('@')}"


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


_EMAIL_SIMPLES = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_CAMPOS_URL_OU_HANDLE = (
    "instagram", "linkedin", "facebook", "tiktok", "youtube", "website"
)


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

    if dados["email"] and not _EMAIL_SIMPLES.fullmatch(dados["email"]):
        erros.append("E-mail em formato inválido.")

    if dados["background_color"] and not _HEX_COLOR.fullmatch(dados["background_color"]):
        erros.append("Cor de fundo deve ser um hexadecimal válido (ex: #05070d).")

    if dados["accent_color"] and not _HEX_COLOR.fullmatch(dados["accent_color"]):
        erros.append("Cor de destaque deve ser um hexadecimal válido (ex: #3b82f6).")

    if dados["google_maps_url"] and not dados["google_maps_url"].startswith(("http://", "https://")):
        erros.append("O link do Google Maps deve ser uma URL válida, iniciando com http:// ou https://.")

    for campo in _CAMPOS_URL_OU_HANDLE:

        if not _valor_sem_esquema_perigoso(dados[campo]):
            erros.append(f"O campo {campo} contém um endereço não permitido.")

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
def redirect_card(card_code: str, request: Request):
    """
    Resolve o acesso público de um cartão NFC/QR Code pelo código —
    mesmo endereço físico impresso/gravado para os dois modos.

    - Não existe: 404.
    - mode=business_card: redireciona (307) para /c/{code}/cartao-visita,
      já que o NFC/QR físico só conhece este endereço.
    - custom_link, mas ainda não está configurado: página pública informativa.
    - custom_link e está configurado: redireciona (307) para o target_url.
    """

    resultado = resolver_cartao_publico(card_code)

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "business_card":
        return RedirectResponse(url=f"/c/{card_code}/cartao-visita", status_code=307)

    if resultado["status"] == "unconfigured":

        return templates.TemplateResponse(
            request=request,
            name="card_unconfigured.html",
            context={}
        )

    return RedirectResponse(url=resultado["target_url"], status_code=307)


@router.get("/c/{card_code}/cartao-visita")
def card_business_profile(card_code: str, request: Request):
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

        return templates.TemplateResponse(
            request=request,
            name="business_card_pending.html",
            context={}
        )

    cor_fundo = _cor_fundo_valida(perfil.background_color)
    cor_destaque = _cor_destaque_valida(perfil.accent_color)

    return templates.TemplateResponse(
        request=request,
        name="business_card.html",
        context={
            "nome": perfil.name,
            "cargo": perfil.professional_title,
            "empresa": perfil.company,
            "foto": _url_segura(perfil.profile_photo),
            "bio": perfil.bio,
            "whatsapp_link": _link_whatsapp(perfil.whatsapp),
            "telefone_link": _link_telefone(perfil.phone),
            "email_link": _link_email(perfil.email),
            "instagram_link": _url_rede_social("https://instagram.com/", perfil.instagram),
            "linkedin_link": _url_rede_social("https://linkedin.com/in/", perfil.linkedin),
            "facebook_link": _url_rede_social("https://facebook.com/", perfil.facebook),
            "tiktok_link": _url_rede_social("https://tiktok.com/@", perfil.tiktok),
            "youtube_link": _url_rede_social("https://youtube.com/", perfil.youtube),
            "website_link": _link_website(perfil.website),
            "google_maps_link": _url_segura(perfil.google_maps_url),
            "pix_key": perfil.pix_key,
            "pix_key_type": perfil.pix_key_type,
            "cor_fundo": cor_fundo,
            "texto_claro": _texto_claro_sobre_fundo(cor_fundo),
            "cor_destaque": cor_destaque,
            "cor_destaque_soft": _cor_com_opacidade(cor_destaque, 0.16),
            "cor_destaque_texto": "#ffffff" if _texto_claro_sobre_fundo(cor_destaque) else "#111827"
        }
    )


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


def _renderizar_pagina_edicao(
    request: Request,
    card_code: str,
    current_user,
    erro=None,
    sucesso=None,
    dados_pendentes=None,
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
    # foto_atual reflete sempre o que está de fato salvo no banco, nunca
    # o dict de dados pendentes (que não inclui foto — ver save_business_profile)
    foto_atual = _url_segura(perfil_real.profile_photo) if perfil_real else None

    return templates.TemplateResponse(
        request=request,
        name="edit_card.html",
        context={
            "cartao": cartao,
            "perfil": perfil,
            "foto_atual": foto_atual,
            "url_cartao_fisico": construir_url_publica_cartao(cartao.code),
            "url_qr_cartao": f"/cards/{cartao.code}/qr",
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

    conteudo_foto = None
    content_type_foto = None

    arquivo_foto = form.get("profile_photo_file")

    if isinstance(arquivo_foto, UploadFile) and arquivo_foto.filename:

        conteudo_foto = await arquivo_foto.read()
        content_type_foto, erro_foto = _validar_foto(conteudo_foto)

        if erro_foto:
            erros.append(erro_foto)

    if erros:

        return _renderizar_pagina_edicao(
            request,
            card_code,
            current_user,
            erro=" ".join(erros),
            dados_pendentes=dados,
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

    definir_modo_cartao(card_code, owner_id=current_user.id, mode="business_card")

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
