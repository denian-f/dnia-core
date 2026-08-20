import io
import secrets
import string
import unicodedata
from decimal import Decimal, ROUND_HALF_UP

import qrcode
from fpdf import FPDF
from PIL import Image
from qrcode.constants import ERROR_CORRECT_M

from app.dna_connect.cards.repository import CardRepository
from app.dna_connect.cards.business_profile_repository import CardBusinessProfileRepository
from app.dna_connect.cards.card_links_repository import CardLinksRepository
from app.dna_connect.users.service import buscar_usuario_por_email
from app.dna_connect.email import config as email_config


MODOS_VALIDOS = ("custom_link", "business_card")

_CODE_PREFIX = "DNAC"
_CODE_SUFFIX_LENGTH = 6
_CODE_ALPHABET = string.ascii_uppercase + string.digits


def gerar_codigo_cartao() -> str:
    """
    Sorteia um código no mesmo padrão usado pelo cadastro manual
    (ex: DNAC-A7K9P2): prefixo fixo + 6 caracteres alfanuméricos
    maiúsculos, usando o gerador do módulo secrets (não determinístico,
    adequado para geração de identificadores). Não garante unicidade
    sozinho — quem chamar precisa checar colisão contra o banco antes
    de persistir (ver gerar_cartao_automatico_admin, em admin/service).
    """

    sufixo = "".join(
        secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_SUFFIX_LENGTH)
    )

    return f"{_CODE_PREFIX}-{sufixo}"


def init_cards_db():
    """
    Garante a existência da tabela de cartões, do relacionamento
    com usuários, da coluna de modo (mode), da tabela de perfil de
    cartão de visita e do cartão de teste.
    """

    repo = CardRepository()

    try:

        repo.criar_tabela()
        repo.criar_relacionamento_owner()
        repo.permitir_target_url_nulo()
        repo.adicionar_coluna_mode()
        repo.seed_cartao_teste()

    finally:

        repo.fechar()

    perfil_repo = CardBusinessProfileRepository()

    try:

        perfil_repo.criar_tabela()
        perfil_repo.adicionar_colunas_foto_upload()
        perfil_repo.adicionar_colunas_personalizacao()
        perfil_repo.adicionar_colunas_fundo_avancado()
        perfil_repo.adicionar_colunas_pix_cobranca()

    finally:

        perfil_repo.fechar()

    links_repo = CardLinksRepository()

    try:

        links_repo.criar_tabela()
        links_repo.migrar_redes_legadas()

    finally:

        links_repo.fechar()


def resolver_cartao_publico(code: str):
    """
    Resolve o acesso público de um cartão (rota GET /c/{card_code}),
    diferenciando quatro estados: inexistente, em mode=business_card
    (o QR Code e o NFC físico sempre codificam /c/{code}, então esse
    endereço precisa levar ao cartão de visita quando for esse o modo
    ativo), existente porém ainda não configurado, ou configurado
    (pronto para redirecionar via target_url).
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(code)

    finally:

        repo.fechar()

    if not card:
        return {"status": "not_found"}

    if card.mode == "business_card":
        return {"status": "business_card"}

    if card.activated and card.target_url:
        return {"status": "configured", "target_url": card.target_url}

    return {"status": "unconfigured"}


def ativar_cartao(email: str, card_code: str):
    """
    Associa um cartão a um usuário já cadastrado e o marca como ativado.
    """

    user = buscar_usuario_por_email(email)

    if not user:
        return {"status": "unauthorized"}

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

        if not card:
            return {"status": "not_found"}

        if card.activated:
            return {"status": "already_activated"}

        repo.vincular_usuario(code=card_code, owner_id=user.id)

    finally:

        repo.fechar()

    return {
        "status": "activated",
        "card_code": card_code,
        "user": user
    }


def atualizar_link_cartao(card_code: str, owner_id: int, target_url: str):
    """
    Atualiza o target_url de um cartão, caso pertença ao usuário informado.
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

        if not card:
            return {"status": "not_found"}

        if card.owner_id != owner_id:
            return {"status": "forbidden"}

        repo.atualizar_target_url(code=card_code, target_url=target_url)

    finally:

        repo.fechar()

    return {
        "status": "updated",
        "card_code": card_code,
        "target_url": target_url
    }


def remover_cartao(card_code: str, owner_id: int):
    """
    Remove a associação de um cartão com o usuário (remoção lógica): o
    cartão nunca é apagado, apenas volta ao estado anterior à ativação.
    O modo volta para custom_link e o perfil de cartão de visita
    associado é apagado, para que um futuro proprietário do mesmo
    código físico nunca herde mode/dados de quem usou o cartão antes.
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

        if not card:
            return {"status": "not_found"}

        if card.owner_id != owner_id:
            return {"status": "forbidden"}

        repo.remover_associacao(code=card_code)

    finally:

        repo.fechar()

    perfil_repo = CardBusinessProfileRepository()

    try:

        perfil_repo.remover_por_card_id(card.id)

    finally:

        perfil_repo.fechar()

    return {"status": "removed", "card_code": card_code}


def listar_cartoes_por_owner(owner_id: int):
    """
    Retorna todos os cartões pertencentes a um usuário.
    """

    repo = CardRepository()

    try:

        return repo.listar_por_owner(owner_id)

    finally:

        repo.fechar()


def obter_cartao(card_code: str, owner_id: int):
    """
    Retorna os dados de um cartão, caso pertença ao usuário informado.
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

        if not card:
            return {"status": "not_found"}

        if card.owner_id != owner_id:
            return {"status": "forbidden"}

    finally:

        repo.fechar()

    return {"status": "ok", "card": card}


def construir_url_publica_cartao(card_code: str) -> str:
    """
    Monta a URL pública permanente do cartão — a mesma usada pelo NFC e
    pelo QR Code: {CARD_BASE_URL}/c/{card_code}. Depende exclusivamente
    do código do cartão, nunca de owner_id, activated ou target_url.

    Usa CARD_BASE_URL (não APP_BASE_URL) de propósito: é o domínio que
    pode ser um subdomínio dedicado ao cartão público (ex:
    card.dominio.com), separado do domínio de login/e-mail.
    """

    return f"{email_config.CARD_BASE_URL}/c/{card_code}"


def definir_modo_cartao(card_code: str, owner_id: int, mode: str):
    """
    Define o modo de utilização do cartão (custom_link ou business_card).
    Um cartão só pode estar em um modo por vez — a troca simplesmente
    substitui o valor do campo, nunca os dois coexistem.
    """

    if mode not in MODOS_VALIDOS:
        return {"status": "invalid_mode"}

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

        if not card:
            return {"status": "not_found"}

        if card.owner_id != owner_id:
            return {"status": "forbidden"}

        repo.atualizar_modo(code=card_code, mode=mode)

    finally:

        repo.fechar()

    return {"status": "updated", "card_code": card_code, "mode": mode}


def salvar_perfil_cartao_visita(card_code: str, owner_id: int, dados: dict):
    """
    Cria ou atualiza os dados do cartão de visita digital de um cartão
    (INSERT/UPDATE via upsert). Todos os campos são opcionais: os que
    não forem informados em `dados` ficam como NULL. Não exige que o
    cartão já esteja em mode=business_card — apenas o modo ativo
    determina o que é efetivamente utilizado na resolução pública.
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

        if not card:
            return {"status": "not_found"}

        if card.owner_id != owner_id:
            return {"status": "forbidden"}

    finally:

        repo.fechar()

    perfil_repo = CardBusinessProfileRepository()

    try:

        perfil_repo.salvar(card_id=card.id, dados=dados)

    finally:

        perfil_repo.fechar()

    return {"status": "saved", "card_code": card_code}


def listar_links_cartao_visita(card_id: int):
    """
    Lista os links livres do cartão (Sprint 4 do roadmap Airgo, no
    lugar dos antigos campos fixos de rede social), na ordem
    configurada pelo dono.
    """

    links_repo = CardLinksRepository()

    try:

        return links_repo.listar_por_card_id(card_id)

    finally:

        links_repo.fechar()


def salvar_links_cartao_visita(card_code: str, owner_id: int, links: list):
    """
    Substitui a lista de links livres do cartão. Reaproveita a mesma
    checagem de posse de salvar_perfil_cartao_visita.
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

        if not card:
            return {"status": "not_found"}

        if card.owner_id != owner_id:
            return {"status": "forbidden"}

    finally:

        repo.fechar()

    links_repo = CardLinksRepository()

    try:

        links_repo.substituir_links(card_id=card.id, links=links)

    finally:

        links_repo.fechar()

    return {"status": "saved", "card_code": card_code}


def construir_url_foto_cartao(card_code: str) -> str:
    """
    Caminho interno (relativo, sem domínio) que serve a foto de perfil
    enviada por upload — mesma URL usada tanto na página pública
    quanto no editor.
    """

    return f"/c/{card_code}/photo"


def salvar_foto_cartao_visita(card_code: str, owner_id: int, dados_binarios: bytes, content_type: str):
    """
    Salva a foto de perfil enviada por upload (Sprint 28). Substitui
    qualquer foto anterior (upload ou URL manual da Sprint 26) — só
    existe uma foto ativa por cartão. Valida a posse do cartão antes
    de gravar.
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

        if not card:
            return {"status": "not_found"}

        if card.owner_id != owner_id:
            return {"status": "forbidden"}

    finally:

        repo.fechar()

    perfil_repo = CardBusinessProfileRepository()

    try:

        perfil_repo.salvar_foto(
            card_id=card.id,
            dados_binarios=dados_binarios,
            content_type=content_type,
            url_publica=construir_url_foto_cartao(card_code)
        )

    finally:

        perfil_repo.fechar()

    return {"status": "saved", "card_code": card_code}


def remover_foto_cartao_visita(card_code: str, owner_id: int):
    """
    Remove a foto de perfil do cartão (volta ao placeholder/inicial da
    página pública). Não afeta os demais campos do perfil.
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

        if not card:
            return {"status": "not_found"}

        if card.owner_id != owner_id:
            return {"status": "forbidden"}

    finally:

        repo.fechar()

    perfil_repo = CardBusinessProfileRepository()

    try:

        perfil_repo.remover_foto(card_id=card.id)

    finally:

        perfil_repo.fechar()

    return {"status": "removed", "card_code": card_code}


def obter_foto_cartao_visita(card_code: str):
    """
    Retorna os bytes/content-type da foto ativa de um cartão para a
    rota pública que serve a imagem (GET /c/{card_code}/photo). Não
    faz verificação de dono — a foto é um recurso público, exposto na
    mesma página pública do cartão de visita.
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

    finally:

        repo.fechar()

    if not card:
        return None

    perfil_repo = CardBusinessProfileRepository()

    try:

        return perfil_repo.buscar_foto_por_card_id(card.id)

    finally:

        perfil_repo.fechar()


def construir_url_imagem_fundo_cartao(card_code: str) -> str:
    """
    Caminho interno (relativo, sem domínio) que serve a imagem de fundo
    do cartão de visita enviada por upload — mesmo padrão de
    construir_url_foto_cartao, para a segunda imagem opcional do perfil.
    """

    return f"/c/{card_code}/background-image"


def salvar_imagem_fundo_cartao_visita(card_code: str, owner_id: int, dados_binarios: bytes, content_type: str):
    """
    Salva a imagem de fundo (background_type = image) enviada por
    upload. Substitui qualquer imagem de fundo anterior — só existe uma
    imagem de fundo ativa por cartão. Valida a posse do cartão antes de
    gravar, exatamente como salvar_foto_cartao_visita.
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

        if not card:
            return {"status": "not_found"}

        if card.owner_id != owner_id:
            return {"status": "forbidden"}

    finally:

        repo.fechar()

    perfil_repo = CardBusinessProfileRepository()

    try:

        perfil_repo.salvar_imagem_fundo(
            card_id=card.id,
            dados_binarios=dados_binarios,
            content_type=content_type,
            url_publica=construir_url_imagem_fundo_cartao(card_code)
        )

    finally:

        perfil_repo.fechar()

    return {"status": "saved", "card_code": card_code}


def remover_imagem_fundo_cartao_visita(card_code: str, owner_id: int):
    """
    Remove a imagem de fundo do cartão de visita. Não afeta os demais
    campos do perfil nem o background_type salvo (se o cartão continuar
    marcado como mode=image sem imagem, a renderização pública cai de
    volta para a cor sólida padrão — ver card_business_profile).
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

        if not card:
            return {"status": "not_found"}

        if card.owner_id != owner_id:
            return {"status": "forbidden"}

    finally:

        repo.fechar()

    perfil_repo = CardBusinessProfileRepository()

    try:

        perfil_repo.remover_imagem_fundo(card_id=card.id)

    finally:

        perfil_repo.fechar()

    return {"status": "removed", "card_code": card_code}


def obter_imagem_fundo_cartao_visita(card_code: str):
    """
    Retorna os bytes/content-type da imagem de fundo ativa de um
    cartão, para a rota pública que serve a imagem. Não faz verificação
    de dono — mesmo nível de exposição de obter_foto_cartao_visita.
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

    finally:

        repo.fechar()

    if not card:
        return None

    perfil_repo = CardBusinessProfileRepository()

    try:

        return perfil_repo.buscar_imagem_fundo_por_card_id(card.id)

    finally:

        perfil_repo.fechar()


def obter_perfil_cartao_visita_editor(card_code: str, owner_id: int):
    """
    Retorna o cartão e o perfil de cartão de visita associados,
    independentemente do modo atual, para uso na tela de edição do
    proprietário (diferente de resolver_cartao_visita, que só retorna
    dados quando mode=business_card — aqui os dados do perfil precisam
    continuar visíveis/editáveis mesmo quando o cartão está em
    custom_link, conforme a regra definida na Sprint 24).
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

    finally:

        repo.fechar()

    if not card:
        return {"status": "not_found"}

    if card.owner_id != owner_id:
        return {"status": "forbidden"}

    perfil_repo = CardBusinessProfileRepository()

    try:

        perfil = perfil_repo.buscar_por_card_id(card.id)

    finally:

        perfil_repo.fechar()

    links = listar_links_cartao_visita(card.id)

    return {"status": "ok", "card": card, "profile": perfil, "links": links}


def resolver_cartao_visita(card_code: str):
    """
    Resolve o acesso à página de cartão de visita digital de um cartão
    (rota GET /c/{card_code}/cartao-visita). Retorna o perfil apenas
    quando o cartão existe e está no modo business_card.
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

    finally:

        repo.fechar()

    if not card:
        return {"status": "not_found"}

    if card.mode != "business_card":
        return {"status": "wrong_mode", "mode": card.mode}

    perfil_repo = CardBusinessProfileRepository()

    try:

        perfil = perfil_repo.buscar_por_card_id(card.id)

    finally:

        perfil_repo.fechar()

    links = listar_links_cartao_visita(card.id)

    return {"status": "ok", "card_code": card.code, "profile": perfil, "links": links}


_QR_RESOLUCAO_MINIMA_PX = 1000
_QR_BORDA_MODULOS = 4  # quiet zone mínima recomendada pela especificação QR


def _renderizar_qr_code(conteudo: str) -> bytes:
    """
    Renderiza qualquer texto como imagem PNG de QR Code (em memória,
    nunca persistida em disco). Extraído de gerar_qr_code_cartao para
    ser reaproveitado também pelo QR Code offline (vCard) — a lógica de
    renderização é a mesma, só muda o que é codificado.

    Resolução calculada dinamicamente (>= 1000x1000px) para ficar
    adequada à impressão física do cartão (Sprint 29) — mesma técnica
    já usada no utilitário de QR de embalagem da Sprint 24.
    """

    qr = qrcode.QRCode(
        error_correction=ERROR_CORRECT_M,
        box_size=10,
        border=_QR_BORDA_MODULOS,
    )
    qr.add_data(conteudo)
    qr.make(fit=True)

    modulos_totais = len(qr.get_matrix())  # já inclui a quiet zone
    qr.box_size = -(-_QR_RESOLUCAO_MINIMA_PX // modulos_totais)  # ceil division

    imagem = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")

    return buffer.getvalue()


def gerar_qr_code_cartao(card_code: str):
    """
    Gera a imagem PNG do QR Code que aponta para a URL pública
    permanente do cartão. Retorna None caso o cartão não exista.
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

    finally:

        repo.fechar()

    if not card:
        return None

    url = construir_url_publica_cartao(card.code)

    return _renderizar_qr_code(url)


def _escapar_valor_vcard(valor: str) -> str:
    """
    Escapa caracteres especiais reservados pelo formato vCard (RFC
    6350), evitando um arquivo malformado caso nome/empresa/cargo
    contenham vírgula, ponto e vírgula ou barra invertida.
    """

    return (
        valor.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def construir_vcard_cartao_visita(perfil) -> str:
    """
    Monta um vCard 3.0 (padrão universal reconhecido nativamente por
    qualquer celular, sem precisar de app nem internet para ler) a
    partir do perfil do cartão de visita. Fonte compartilhada tanto
    pelo botão "Salvar contato" (download .vcf) quanto pelo QR Code
    offline — só muda o destino do mesmo conteúdo.

    Mantém apenas os campos de identidade/contato "de cartão físico"
    (nome, cargo, empresa, telefone, e-mail, site). Bio, redes sociais
    e Pix ficam de fora de propósito: são dados da página pública
    completa, não fazem parte de um cartão de visita tradicional, e
    deixariam o QR Code denso demais para escanear de forma confiável.
    """

    nome = _escapar_valor_vcard((perfil.name or "").strip()) or "Sem nome"

    linhas = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{nome};;;;",
        f"FN:{nome}"
    ]

    if perfil.company:
        linhas.append(f"ORG:{_escapar_valor_vcard(perfil.company.strip())}")

    if perfil.professional_title:
        linhas.append(f"TITLE:{_escapar_valor_vcard(perfil.professional_title.strip())}")

    telefone = perfil.whatsapp or perfil.phone

    if telefone:
        linhas.append(f"TEL;TYPE=CELL:{_escapar_valor_vcard(telefone.strip())}")

    if perfil.email:
        linhas.append(f"EMAIL:{_escapar_valor_vcard(perfil.email.strip())}")

    if perfil.website:

        site = perfil.website.strip()

        if not site.startswith(("http://", "https://")):
            site = f"https://{site}"

        linhas.append(f"URL:{_escapar_valor_vcard(site)}")

    linhas.append("END:VCARD")

    return "\r\n".join(linhas) + "\r\n"


def obter_vcard_cartao_visita(card_code: str):
    """
    Retorna o vCard do cartão de visita público (rota GET
    /c/{card_code}/vcard), ou None caso o cartão não exista, não esteja
    em modo business_card, ou ainda não tenha perfil preenchido — mesmo
    padrão de resolver_cartao_visita, sem exigir autenticação (é dado
    já público na própria página do cartão).
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

    finally:

        repo.fechar()

    if not card or card.mode != "business_card":
        return None

    perfil_repo = CardBusinessProfileRepository()

    try:

        perfil = perfil_repo.buscar_por_card_id(card.id)

    finally:

        perfil_repo.fechar()

    if not perfil:
        return None

    return construir_vcard_cartao_visita(perfil)


def gerar_qr_code_offline_cartao(card_code: str):
    """
    QR Code "offline": em vez de apontar para a página pública do
    cartão, o próprio conteúdo do QR é o vCard — o celular reconhece o
    formato e oferece salvar direto nos contatos, sem precisar de
    internet no momento do scan (diferente do QR "online", que exige
    carregar a página). Retorna None nos mesmos casos de
    obter_vcard_cartao_visita (cartão inexistente, modo custom_link, ou
    sem perfil preenchido — não há dados para montar um vCard).
    """

    vcard = obter_vcard_cartao_visita(card_code)

    if not vcard:
        return None

    return _renderizar_qr_code(vcard)


_PIX_TAMANHO_MAXIMO_CHAVE = 77
_PIX_TAMANHO_MAXIMO_NOME = 25
_PIX_TAMANHO_MAXIMO_CIDADE = 15


def _tlv_pix(id_campo: str, valor: str) -> str:
    """
    Formata um campo do payload Pix no padrão EMV/BR Code do Banco
    Central: identificador (2 dígitos) + tamanho (2 dígitos) + valor.
    Todo o payload é uma sequência desses campos concatenados.
    """

    return f"{id_campo}{len(valor):02d}{valor}"


def _crc16_ccitt_pix(payload: str) -> str:
    """
    CRC16/CCITT-FALSE (polinômio 0x1021, valor inicial 0xFFFF) — o
    checksum de 4 dígitos hexadecimais exigido no final de todo
    payload Pix, calculado sobre o payload inteiro já incluindo o
    próprio campo do CRC com o valor ainda vazio ("6304").
    """

    crc = 0xFFFF

    for caractere in payload:

        crc ^= ord(caractere) << 8

        for _ in range(8):

            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF

    return f"{crc:04X}"


def _sanitizar_texto_pix(texto: str) -> str:
    """
    O payload Pix só aceita um conjunto restrito de caracteres (sem
    acentuação) nos campos de nome/cidade do beneficiário — remove
    acentos e qualquer caractere que não seja letra/número/espaço.
    """

    normalizado = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(c for c in normalizado if unicodedata.category(c) != "Mn")

    return "".join(c for c in sem_acento if c.isalnum() or c.isspace()).strip()


def construir_payload_pix(chave: str, nome_beneficiario: str, cidade_beneficiario: str, valor=None) -> str:
    """
    Monta o payload do QR Code Pix ("BR Code"), no formato oficial
    publicado pelo Banco Central — não depende de nenhum gateway de
    pagamento nem de credenciais externas: é só uma string de texto
    seguindo essa especificação pública, que qualquer app de banco
    compatível com Pix sabe ler.

    Importante: isso apenas GERA o código de cobrança. O DNA Connect
    não recebe nenhuma confirmação de que o pagamento foi feito — isso
    só o próprio banco do beneficiário sabe. Uma confirmação
    automática exigiria integração real com um gateway/API bancária,
    fora do escopo combinado para esta sprint.

    `valor` é opcional: se informado, vem pré-preenchido no app de
    quem for pagar; se omitido, o pagador digita o valor manualmente.
    """

    nome = _sanitizar_texto_pix(nome_beneficiario)[:_PIX_TAMANHO_MAXIMO_NOME] or "NAO INFORMADO"
    cidade = _sanitizar_texto_pix(cidade_beneficiario)[:_PIX_TAMANHO_MAXIMO_CIDADE] or "NAO INFORMADO"
    chave = chave.strip()[:_PIX_TAMANHO_MAXIMO_CHAVE]

    conta_pix = _tlv_pix("00", "BR.GOV.BCB.PIX") + _tlv_pix("01", chave)

    campos = [
        _tlv_pix("00", "01"),   # Payload Format Indicator
        _tlv_pix("01", "11"),   # Point of Initiation Method (11 = estático/reutilizável)
        _tlv_pix("26", conta_pix),  # Merchant Account Information (dados da chave Pix)
        _tlv_pix("52", "0000"),  # Merchant Category Code (genérico)
        _tlv_pix("53", "986"),   # Transaction Currency (986 = BRL)
    ]

    if valor is not None:

        valor_formatado = str(Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        campos.append(_tlv_pix("54", valor_formatado))  # Transaction Amount

    campos.append(_tlv_pix("58", "BR"))  # Country Code
    campos.append(_tlv_pix("59", nome))  # Merchant Name (beneficiário)
    campos.append(_tlv_pix("60", cidade))  # Merchant City (beneficiário)
    campos.append(_tlv_pix("62", _tlv_pix("05", "***")))  # Additional Data (sem txid específico)

    payload_para_crc = "".join(campos) + "6304"

    return payload_para_crc + _crc16_ccitt_pix(payload_para_crc)


def obter_payload_pix_cartao(card_code: str, valor=None):
    """
    Monta o payload Pix de cobrança do cartão, a partir da chave e dos
    dados de beneficiário salvos no perfil. Retorna None se o cartão
    não existir, não estiver em modo business_card, ou não tiver os
    três dados obrigatórios preenchidos (chave, nome e cidade do
    beneficiário) — sem eles não é possível montar um payload válido.
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

    finally:

        repo.fechar()

    if not card or card.mode != "business_card":
        return None

    perfil_repo = CardBusinessProfileRepository()

    try:

        perfil = perfil_repo.buscar_por_card_id(card.id)

    finally:

        perfil_repo.fechar()

    if not perfil or not perfil.pix_key or not perfil.pix_beneficiary_name or not perfil.pix_beneficiary_city:
        return None

    return construir_payload_pix(
        chave=perfil.pix_key,
        nome_beneficiario=perfil.pix_beneficiary_name,
        cidade_beneficiario=perfil.pix_beneficiary_city,
        valor=valor
    )


def gerar_qr_code_pix_cartao(card_code: str, valor=None):
    """
    Gera a imagem PNG do QR Code de cobrança Pix do cartão. Retorna
    None nos mesmos casos de obter_payload_pix_cartao.
    """

    payload = obter_payload_pix_cartao(card_code, valor=valor)

    if not payload:
        return None

    return _renderizar_qr_code(payload)


_PDF_COR_MARCA = (8, 94, 254)      # --dc-brand
_PDF_COR_NAVY = (11, 31, 74)       # --dc-navy
_PDF_COR_CINZA = (107, 114, 128)   # --dc-gray-500
_PDF_COR_CINZA_CLARO = (229, 232, 239)  # --dc-gray-200

def _imagem_para_pdf(dados_binarios: bytes):
    """
    Normaliza qualquer imagem suportada pelo upload (JPG/PNG/WEBP) para
    PNG em memória — fpdf2 lida de forma mais previsível com PNG/JPEG
    do que com WEBP, então convertemos aqui em vez de arriscar
    incompatibilidade silenciosa na geração do PDF.
    """

    imagem = Image.open(io.BytesIO(dados_binarios)).convert("RGB")
    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer


def _montar_pdf_cartao_visita(perfil, url_publica: str, qr_bytes: bytes, foto_bytes, links: list) -> bytes:
    """
    Monta o PDF do cartão de visita digital, como um documento de uma
    página (A4) — pra baixar e anexar em e-mail/WhatsApp, diferente do
    QR Code/vCard (pensados para escaneamento). Layout desenhado
    programaticamente com fpdf2 (sem dependência nativa do sistema
    operacional, ao contrário do WeasyPrint já usado em outro módulo do
    projeto — evita o mesmo problema de ambiente), não é uma conversão
    do HTML da página pública.
    """

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    # As fontes padrão (Helvetica) não convertem a codificação sozinhas
    # — sem isso, acentos (ã, õ, ç...) viram caracteres inválidos no
    # PDF gerado. cp1252 cobre todos os caracteres usados em português.
    pdf.core_fonts_encoding = "cp1252"
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    largura_pagina = pdf.w
    margem = pdf.l_margin
    largura_util = largura_pagina - 2 * margem

    # Barra de marca no topo
    pdf.set_fill_color(*_PDF_COR_MARCA)
    pdf.rect(0, 0, largura_pagina, 6, style="F")

    pdf.set_xy(margem, 16)

    largura_foto = 32

    if foto_bytes:

        pdf.image(_imagem_para_pdf(foto_bytes), x=margem, y=16, w=largura_foto, h=largura_foto)
        x_texto = margem + largura_foto + 8

    else:

        x_texto = margem

    largura_texto = largura_pagina - margem - x_texto

    pdf.set_xy(x_texto, 18)
    pdf.set_text_color(*_PDF_COR_NAVY)
    pdf.set_font("Helvetica", style="B", size=20)
    pdf.multi_cell(largura_texto, 9, perfil.name or "Sem nome", align="L")

    if perfil.professional_title or perfil.company:

        subtitulo = " · ".join(filter(None, [perfil.professional_title, perfil.company]))
        pdf.set_x(x_texto)
        pdf.set_font("Helvetica", size=12)
        pdf.set_text_color(*_PDF_COR_CINZA)
        pdf.multi_cell(largura_texto, 6, subtitulo, align="L")

    pdf.set_y(max(pdf.get_y(), 16 + largura_foto) + 8)

    pdf.set_draw_color(*_PDF_COR_CINZA_CLARO)
    pdf.line(margem, pdf.get_y(), largura_pagina - margem, pdf.get_y())
    pdf.ln(8)

    if perfil.bio:

        pdf.set_font("Helvetica", size=11)
        pdf.set_text_color(*_PDF_COR_NAVY)
        pdf.multi_cell(largura_util, 6, perfil.bio, align="L")
        pdf.ln(4)

    def linha_contato(rotulo: str, valor: str):
        """
        Desenha "rótulo | valor" numa linha, posicionando cada célula
        explicitamente (em vez de encadear cell() -> multi_cell() e
        confiar no avanço automático do cursor do fpdf2, que causava
        sobreposição/corte quando o valor quebrava em mais de uma linha).
        """

        if not valor:
            return

        y_inicio = pdf.get_y()

        pdf.set_xy(margem, y_inicio)
        pdf.set_font("Helvetica", style="B", size=10)
        pdf.set_text_color(*_PDF_COR_CINZA)
        pdf.cell(32, 7, rotulo)

        pdf.set_xy(margem + 32, y_inicio)
        pdf.set_font("Helvetica", size=11)
        pdf.set_text_color(*_PDF_COR_NAVY)
        pdf.multi_cell(largura_util - 32, 7, valor, align="L")

        pdf.set_xy(margem, max(pdf.get_y(), y_inicio + 7))

    linha_contato("WhatsApp", perfil.whatsapp)
    linha_contato("Telefone", perfil.phone)
    linha_contato("E-mail", perfil.email)
    linha_contato("Site", perfil.website)
    linha_contato("Localização", perfil.google_maps_url)

    if links:

        pdf.ln(2)

        for link in links:
            linha_contato(link["label"], link["url"])

    if perfil.pix_key:

        pdf.ln(2)
        rotulo_pix = f"Pix ({perfil.pix_key_type})" if perfil.pix_key_type else "Pix"
        linha_contato(rotulo_pix, perfil.pix_key)

    # A partir daqui o posicionamento é controlado manualmente (QR Code
    # e rodapé ficam propositalmente dentro da margem inferior) — sem
    # desligar a quebra automática, fpdf2 insere uma segunda página só
    # pra caber o rodapé, mesmo cabendo tudo numa página só.
    pdf.set_auto_page_break(auto=False)

    # QR Code + link, no rodapé da página
    tamanho_qr = 32
    y_qr = pdf.h - pdf.b_margin - tamanho_qr - 12

    if pdf.get_y() < y_qr:
        pdf.set_y(y_qr)
    else:
        pdf.add_page()
        pdf.set_y(pdf.h - pdf.b_margin - tamanho_qr - 12)

    y_qr = pdf.get_y()

    pdf.image(io.BytesIO(qr_bytes), x=margem, y=y_qr, w=tamanho_qr, h=tamanho_qr)

    pdf.set_xy(margem + tamanho_qr + 8, y_qr + 6)
    pdf.set_font("Helvetica", style="B", size=11)
    pdf.set_text_color(*_PDF_COR_NAVY)
    pdf.multi_cell(largura_util - tamanho_qr - 8, 6, "Aponte a câmera para abrir o cartão digital", align="L")

    pdf.set_xy(margem + tamanho_qr + 8, pdf.get_y() + 2)
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(*_PDF_COR_CINZA)
    pdf.multi_cell(largura_util - tamanho_qr - 8, 5, url_publica, align="L")

    pdf.set_y(-15)
    pdf.set_font("Helvetica", size=8)
    pdf.set_text_color(*_PDF_COR_CINZA)
    pdf.cell(largura_util, 5, "DNA CONNECT", align="C")

    return bytes(pdf.output())


def gerar_pdf_cartao_visita(card_code: str):
    """
    Gera o PDF do cartão de visita digital (em memória, nunca
    persistido em disco), pronto para download/anexo. Mesmas condições
    do vCard e do QR offline: só existe para cartões em modo
    business_card com perfil preenchido. Reaproveita o QR Code "online"
    já existente (aponta para a página pública, igual ao gravado no
    NFC) e a foto de perfil já enviada, se houver.
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

    finally:

        repo.fechar()

    if not card or card.mode != "business_card":
        return None

    perfil_repo = CardBusinessProfileRepository()

    try:

        perfil = perfil_repo.buscar_por_card_id(card.id)

    finally:

        perfil_repo.fechar()

    if not perfil:
        return None

    url_publica = construir_url_publica_cartao(card.code)
    qr_bytes = _renderizar_qr_code(url_publica)

    foto = obter_foto_cartao_visita(card_code)
    foto_bytes = foto["dados"] if foto else None

    links = listar_links_cartao_visita(card.id)

    return _montar_pdf_cartao_visita(perfil, url_publica, qr_bytes, foto_bytes, links)
