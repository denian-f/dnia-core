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


def listar_cartoes_por_owner(owner_id: int):
    """
    Retorna todos os cartões pertencentes a um usuário.
    """

    repo = CardRepository()

    try:

        return repo.listar_por_owner(owner_id)

    finally:

        repo.fechar()
