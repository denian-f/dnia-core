import io

import qrcode
from qrcode.constants import ERROR_CORRECT_M

from app.dna_connect.cards.repository import CardRepository
from app.dna_connect.cards.business_profile_repository import CardBusinessProfileRepository
from app.dna_connect.users.service import buscar_usuario_por_email
from app.dna_connect.email import config as email_config


MODOS_VALIDOS = ("custom_link", "business_card")


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

    finally:

        perfil_repo.fechar()


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
    pelo QR Code: {APP_BASE_URL}/c/{card_code}. Depende exclusivamente
    do código do cartão, nunca de owner_id, activated ou target_url.
    """

    return f"{email_config.APP_BASE_URL}/c/{card_code}"


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

    return {"status": "ok", "card": card, "profile": perfil}


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

    return {"status": "ok", "card_code": card.code, "profile": perfil}


_QR_RESOLUCAO_MINIMA_PX = 1000
_QR_BORDA_MODULOS = 4  # quiet zone mínima recomendada pela especificação QR


def gerar_qr_code_cartao(card_code: str):
    """
    Gera a imagem PNG (em memória, nunca persistida em disco) do QR Code
    que aponta para a URL pública permanente do cartão. Retorna None
    caso o cartão não exista.

    Resolução calculada dinamicamente (>= 1000x1000px) para ficar
    adequada à impressão física do cartão (Sprint 29) — mesma técnica
    já usada no utilitário de QR de embalagem da Sprint 24. O conteúdo
    codificado (a URL) não muda.
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

    finally:

        repo.fechar()

    if not card:
        return None

    url = construir_url_publica_cartao(card.code)

    qr = qrcode.QRCode(
        error_correction=ERROR_CORRECT_M,
        box_size=10,
        border=_QR_BORDA_MODULOS,
    )
    qr.add_data(url)
    qr.make(fit=True)

    modulos_totais = len(qr.get_matrix())  # já inclui a quiet zone
    qr.box_size = -(-_QR_RESOLUCAO_MINIMA_PX // modulos_totais)  # ceil division

    imagem = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")

    return buffer.getvalue()
