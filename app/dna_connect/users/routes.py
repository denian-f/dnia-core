from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.dna_connect.users.service import (
    registrar_usuario,
    autenticar_usuario,
    listar_cartoes_do_usuario,
    atualizar_perfil_usuario
)
from app.dna_connect.auth.jwt import gerar_token
from app.dna_connect.auth.dependencies import get_current_user, get_optional_user

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)

PROFILE_ERROR_MESSAGES = {
    "name_required": "Nome é obrigatório.",
    "email_required": "E-mail é obrigatório.",
    "invalid_email": "E-mail inválido.",
    "email_exists": "Este e-mail já está em uso por outro usuário."
}


class RegisterRequest(BaseModel):

    name: str
    email: str
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Denian Fernandes",
                "email": "denian@email.com",
                "password": "minhasenha123"
            }
        }
    }


class LoginRequest(BaseModel):

    email: str
    password: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "denian@email.com",
                "password": "minhasenha123"
            }
        }
    }


@router.post("/register")
def register(payload: RegisterRequest):
    """
    Cria uma conta permanente na plataforma.
    """

    resultado = registrar_usuario(
        name=payload.name,
        email=payload.email,
        password=payload.password
    )

    if resultado["status"] == "email_exists":

        raise HTTPException(
            status_code=409,
            detail="Este e-mail já está cadastrado."
        )

    user = resultado["user"]

    return {
        "message": "Conta criada com sucesso!",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }


@router.post("/login")
def login(payload: LoginRequest):
    """
    Valida e-mail e senha de um usuário e retorna um Bearer Token (JWT).
    """

    resultado = autenticar_usuario(
        email=payload.email,
        password=payload.password
    )

    if resultado["status"] == "invalid_credentials":

        raise HTTPException(
            status_code=401,
            detail="E-mail ou senha inválidos."
        )

    user = resultado["user"]

    access_token = gerar_token(
        user_id=user.id,
        email=user.email
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/users/me/cards")
def get_my_cards(current_user=Depends(get_current_user)):
    """
    Lista os cartões pertencentes ao usuário autenticado.
    """

    resultado = listar_cartoes_do_usuario(current_user.email)

    return [
        {
            "code": card.code,
            "activated": card.activated,
            "target_url": card.target_url
        }
        for card in resultado["cartoes"]
    ]


@router.get("/profile")
def profile_view(
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Renderiza a tela web de perfil do usuário autenticado.
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "usuario": current_user,
            "erro": None,
            "sucesso": None
        }
    )


@router.post("/profile")
async def profile_submit(
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Processa a atualização web do nome/e-mail, reutilizando exatamente o
    Service de atualização de perfil.
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    form = await request.form()
    name = form.get("name", "")
    email = form.get("email", "")

    resultado = atualizar_perfil_usuario(
        user_id=current_user.id,
        name=name,
        email=email
    )

    if resultado["status"] != "updated":

        return templates.TemplateResponse(
            request=request,
            name="profile.html",
            context={
                "usuario": {"name": name, "email": email},
                "erro": PROFILE_ERROR_MESSAGES.get(
                    resultado["status"],
                    "Não foi possível atualizar o perfil."
                ),
                "sucesso": None
            },
            status_code=400
        )

    user = resultado["user"]

    # Reemite o JWT com o e-mail atualizado (o token/cookie usa o e-mail
    # como identificador) e renova o Cookie, mantendo a sessão válida.
    access_token = gerar_token(
        user_id=user.id,
        email=user.email
    )

    response = RedirectResponse(url="/dashboard/view", status_code=302)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax"
    )

    return response
