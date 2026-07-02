from app.config import OWNER_PHONE


def is_owner(phone: str) -> bool:
    """
    Verifica se o número pertence ao proprietário do DNIA Core.
    """

    return phone == OWNER_PHONE