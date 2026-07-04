from app.security.auth import authenticate
from app.state.manager import get_state


PROTECTED_COMMANDS = [
    "crm",
    "cliente",
    "clientes",
    "agenda",
    "calendário",
    "calendario",
    "financeiro",
    "financeira",
    "consignado",
    "dashboard",
    "relatório",
    "relatorio",
]


def is_protected_command(message: str) -> bool:
    """
    Verifica se a mensagem contém um comando protegido.
    """

    message = message.lower()

    return any(command in message for command in PROTECTED_COMMANDS)


def route_message(phone: str, message: str) -> dict:
    """
    Decide como a mensagem deve ser tratada.
    """

    protected = is_protected_command(message)

    if not protected:

        return {
            "protected": False,
            "authenticated": True,
            "session_active": False,
            "role": None,
            "requires_password": False,
            "requires_totp": False,
        }

    auth = authenticate(phone)

    state = get_state(phone)

    session_active = (
        state is not None
        and state["state"] == "AUTHENTICATED"
    )

    return {
        "protected": True,
        "authenticated": auth["authenticated"],
        "session_active": session_active,
        "role": auth["role"],
        "requires_password": auth["requires_password"],
        "requires_totp": auth["requires_totp"],
    }