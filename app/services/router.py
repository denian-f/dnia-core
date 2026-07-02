from app.security.auth import authenticate


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
    Decide se a mensagem precisa de autenticação.

    Retorna um dicionário contendo as informações para o fluxo do DNIA Core.
    """

    protected = is_protected_command(message)

    if not protected:
        return {
            "protected": False,
            "authenticated": True,
            "role": None
        }

    auth = authenticate(phone)

    return {
        "protected": True,
        "authenticated": auth["authenticated"],
        "role": auth["role"],
        "requires_password": auth["requires_password"],
        "requires_totp": auth["requires_totp"]
    }