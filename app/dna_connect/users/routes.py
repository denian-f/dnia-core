from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.dna_connect.users.service import (
    registrar_usuario,
    autenticar_usuario,
    listar_cartoes_do_usuario
)

router = APIRouter()


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
    Valida e-mail e senha de um usuário.
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

    return {
        "message": "Login realizado com sucesso!",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }


@router.get("/users/{email}/cards")
def get_user_cards(email: str):
    """
    Lista os cartões pertencentes ao usuário com o e-mail informado.
    """

    resultado = listar_cartoes_do_usuario(email)

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    return [
        {
            "code": card.code,
            "activated": card.activated,
            "target_url": card.target_url
        }
        for card in resultado["cartoes"]
    ]
