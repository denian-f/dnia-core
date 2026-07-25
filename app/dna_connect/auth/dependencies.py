import jwt as pyjwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.dna_connect.auth.jwt import decodificar_token
from app.dna_connect.users.service import buscar_usuario_por_email

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
):
    """
    Valida o Bearer Token informado e retorna o usuário autenticado.
    """

    if credentials is None:

        raise HTTPException(
            status_code=401,
            detail="Não autenticado. Informe um Bearer Token."
        )

    try:

        payload = decodificar_token(credentials.credentials)

    except pyjwt.PyJWTError:

        raise HTTPException(
            status_code=401,
            detail="Token inválido ou expirado."
        )

    email = payload.get("email")

    user = buscar_usuario_por_email(email) if email else None

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Usuário não encontrado."
        )

    return user
