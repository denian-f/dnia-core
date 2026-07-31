from app.dna_connect.cards.repository import CardRepository
from app.dna_connect.users.service import buscar_usuario_por_email


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


def resolve_target_url(code: str):
    """
    Retorna a URL de destino do cartão, caso exista e esteja ativado.
    """

    repo = CardRepository()

    try:

        card = repo.buscar_por_codigo(code)

    finally:

        repo.fechar()

    if not card or not card.activated:
        return None

    return card.target_url


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
