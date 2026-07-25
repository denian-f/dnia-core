from app.dna_connect.cards.service import listar_cartoes_por_owner


def _contar_cartoes(cartoes):

    total = len(cartoes)
    ativados = sum(1 for card in cartoes if card.activated)

    return {
        "total": total,
        "activated": ativados,
        "inactive": total - ativados
    }


def obter_resumo_dashboard(user):
    """
    Monta o resumo do Dashboard (dados do usuário + contagem de cartões).
    """

    cartoes = listar_cartoes_por_owner(user.id)

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        },
        "cards": _contar_cartoes(cartoes)
    }


def montar_dados_view_dashboard(user):
    """
    Monta os dados completos para a renderização web do Dashboard,
    incluindo a lista de cartões (reaproveitando a mesma consulta).
    """

    cartoes = listar_cartoes_por_owner(user.id)

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        },
        "resumo": _contar_cartoes(cartoes),
        "cartoes": cartoes
    }
