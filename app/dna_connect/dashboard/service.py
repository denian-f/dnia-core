from app.dna_connect.cards.service import listar_cartoes_por_owner


def obter_resumo_dashboard(user):
    """
    Monta o resumo do Dashboard (dados do usuário + contagem de cartões).
    """

    cartoes = listar_cartoes_por_owner(user.id)

    total = len(cartoes)
    ativados = sum(1 for card in cartoes if card.activated)

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        },
        "cards": {
            "total": total,
            "activated": ativados,
            "inactive": total - ativados
        }
    }
