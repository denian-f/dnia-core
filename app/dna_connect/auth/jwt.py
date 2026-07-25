from datetime import datetime, timedelta, timezone

import jwt

from app.dna_connect.auth import config


def gerar_token(user_id: int, email: str) -> str:
    """
    Gera um JWT contendo apenas os dados necessários para identificar o usuário.
    """

    agora = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": agora + timedelta(minutes=config.JWT_EXPIRE_MINUTES)
    }

    return jwt.encode(
        payload,
        config.JWT_SECRET_KEY,
        algorithm=config.JWT_ALGORITHM
    )


def decodificar_token(token: str) -> dict:
    """
    Decodifica e valida um JWT.

    Lança jwt.PyJWTError (assinatura inválida, token expirado, etc.)
    caso o token não seja válido.
    """

    return jwt.decode(
        token,
        config.JWT_SECRET_KEY,
        algorithms=[config.JWT_ALGORITHM]
    )
