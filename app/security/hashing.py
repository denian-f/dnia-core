import bcrypt


def hash_password(password: str) -> str:
    """
    Gera o hash seguro de uma senha em texto puro.
    """

    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verifica se a senha em texto puro corresponde ao hash armazenado.
    """

    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8")
    )
