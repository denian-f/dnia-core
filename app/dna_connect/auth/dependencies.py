import jwt as pyjwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.dna_connect.auth.jwt import decodificar_token
from app.dna_connect.users.service import buscar_usuario_por_email

security_scheme = HTTPBearer(auto_error=False)


def _resolver_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials
):
    """
    Resolve o token a partir do header Authorization (Bearer). Na ausência
    dele, utiliza o Cookie access_token.
    """

    if credentials:
        return credentials.credentials

    return request.cookies.get("access_token")


def _autenticar_por_token(token):
    """
    Decodifica o token e busca o usuário correspondente. Retorna None caso
    o token seja ausente, inválido, expirado ou não corresponda a um
    usuário existente.
    """

    if not token:
        return None

    try:

        payload = decodificar_token(token)

    except pyjwt.PyJWTError:

        return None

    email = payload.get("email")

    return buscar_usuario_por_email(email) if email else None


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
):
    """
    Valida o Bearer Token (header Authorization) ou, na ausência dele,
    o Cookie access_token, e retorna o usuário autenticado.
    """

    token = _resolver_token(request, credentials)

    if not token:

        raise HTTPException(
            status_code=401,
            detail="Não autenticado. Informe um Bearer Token."
        )

    user = _autenticar_por_token(token)

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Token inválido, expirado ou usuário não encontrado."
        )

    return user


def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
):
    """
    Mesma resolução de get_current_user (Bearer ou Cookie), porém nunca
    lança exceção: retorna o usuário autenticado ou None.
    """

    token = _resolver_token(request, credentials)

    return _autenticar_por_token(token)
