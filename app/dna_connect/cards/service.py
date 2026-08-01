import io

import qrcode
from qrcode.constants import ERROR_CORRECT_M

from app.dna_connect.cards.repository import CardRepository
from app.dna_connect.users.service import buscar_usuario_por_email
from app.dna_connect.email import config as email_config


def init_cards_db():
    """
    Garante a existência da tabela de cartões, do relacionamento
    com usuários e do cartão de teste.
    """

    repo = CardRepository()

    try:

        repo.criar_tabela()
        repo.criar_relacionamento_owner()
        repo.permitir_target_url_nulo()
        repo.seed_cartao_teste()

    finally:

        repo.fechar()


def resolver_cartao_publico(code: str):
    """
    Resolve o acesso público de um cartão (rota GET /c/{card_code}),
    diferenciando três estados: inexistente, existente porém ainda não
    configurado, ou configurado (pronto para redirecionar).
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(code)

    finally:

        repo.fechar()

    if not card:
        return {"status": "not_found"}

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


def gerar_qr_code_cartao(card_code: str):
    """
    Gera a imagem PNG (em memória, nunca persistida em disco) do QR Code
    que aponta para a URL pública permanente do cartão. Retorna None
    caso o cartão não exista.
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(card_code)

    finally:

        repo.fechar()

    if not card:
        return None

    url = construir_url_publica_cartao(card.code)

    imagem = qrcode.make(url, error_correction=ERROR_CORRECT_M)

    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")

    return buffer.getvalue()
