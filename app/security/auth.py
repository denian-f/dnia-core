from app.security.permissions import is_owner


def authenticate(phone: str) -> dict:
    """
    Primeira camada de autenticação.
    """

    if is_owner(phone):
        return {
            "authenticated": True,
            "role": "OWNER",
            "requires_password": True,
            "requires_totp": True
        }

    return {
        "authenticated": False,
        "role": None,
        "requires_password": False,
        "requires_totp": False
    }