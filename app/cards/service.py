from app.cards.repository import CardRepository


def init_cards_db():
    """
    Garante a existência da tabela de cartões e do cartão de teste.
    """

    repo = CardRepository()

    try:

        repo.criar_tabela()
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
