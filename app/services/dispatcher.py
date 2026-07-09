from app.state.manager import get_state
from app.services.catalogs.handler import handle_catalog


def dispatch(phone: str, message: str):
    """
    Encaminha a mensagem para o serviço correto.
    """

    state = get_state(phone)

    # ==========================================
    # Usuário já está dentro do módulo Catálogos
    # ==========================================

    if state and state["state"] == "WAITING_CATALOG_CITY":

        return handle_catalog(
            phone=phone,
            message=message
        )

    # ==========================================
    # Menu principal
    # ==========================================

    message = message.strip()

    if state and state["state"] == "WAITING_MENU_OPTION":

        if message == "1":

            return handle_catalog(
                phone=phone,
                message=""
            )

        return (
            "❌ Opção inválida.\n\n"
            "Escolha uma opção válida do menu."
        )

    # ==========================================
    # Nenhum fluxo ativo
    # ==========================================

    return (
        "❌ Nenhum serviço ativo.\n\n"
        "Digite *Serviços DNIA* para acessar o menu."
    )