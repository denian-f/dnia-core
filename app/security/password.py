from app.config import OWNER_PASSWORD


def validate_password(password: str) -> bool:
    """
    Valida a senha do proprietário.
    """

    return password == OWNER_PASSWORD