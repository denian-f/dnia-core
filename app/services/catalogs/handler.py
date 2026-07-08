from app.state.manager import get_state, set_state


def handle_catalog(phone: str, message: str):
    """
    Controla a conversa do módulo de catálogos.
    """

    state = get_state(phone)

    # ==========================
    # Primeira entrada no módulo
    # ==========================

    if (
        not state
        or state["state"] != "WAITING_CATALOG_CITY"
    ):

        set_state(
            phone=phone,
            state="WAITING_CATALOG_CITY"
        )

        return (
            "📄 *Gerador de Catálogos*\n\n"
            "Informe o nome da cidade."
        )

    # ==========================
    # Cidade recebida
    # ==========================

    cidade = message.strip()

    return (
        "✅ Cidade recebida!\n\n"
        f"Cidade: *{cidade}*\n\n"
        "Na próxima etapa iremos gerar o catálogo."
    )