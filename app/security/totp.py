import pyotp

from app.config import TOTP_SECRET


def generate_secret():
    """
    Gera um SECRET para o autenticador.
    """

    return pyotp.random_base32()


def verify_totp(code: str) -> bool:
    """
    Valida um código TOTP informado pelo usuário.
    """

    totp = pyotp.TOTP(TOTP_SECRET)

    return totp.verify(code)