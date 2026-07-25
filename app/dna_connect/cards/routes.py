from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.dna_connect.cards.service import (
    resolve_target_url,
    ativar_cartao,
    atualizar_link_cartao
)
from app.dna_connect.auth.dependencies import get_current_user

router = APIRouter()


class ActivateRequest(BaseModel):

    card_code: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "card_code": "TESTE01"
            }
        }
    }


class UpdateCardRequest(BaseModel):

    target_url: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "target_url": "https://instagram.com/denian_df"
            }
        }
    }


@router.get("/c/{card_code}")
def redirect_card(card_code: str):
    """
    Resolve um cartão NFC pelo código e redireciona para o destino configurado.
    """

    target_url = resolve_target_url(card_code)

    if not target_url:
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    return RedirectResponse(url=target_url, status_code=307)


@router.post("/activate")
def activate_card(
    payload: ActivateRequest,
    current_user=Depends(get_current_user)
):
    """
    Ativa um cartão, associando-o ao usuário autenticado.
    """

    resultado = ativar_cartao(
        email=current_user.email,
        card_code=payload.card_code
    )

    if resultado["status"] == "unauthorized":

        raise HTTPException(
            status_code=401,
            detail="Usuário não encontrado. Cadastre-se em /register antes de ativar um cartão."
        )

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "already_activated":

        raise HTTPException(
            status_code=409,
            detail="Este cartão já está ativado."
        )

    user = resultado["user"]

    return {
        "message": "Cartão ativado com sucesso!",
        "card_code": resultado["card_code"],
        "owner": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }


@router.put("/cards/{card_code}")
def update_card(
    card_code: str,
    payload: UpdateCardRequest,
    current_user=Depends(get_current_user)
):
    """
    Atualiza o link (target_url) de um cartão pertencente ao usuário autenticado.
    """

    if not payload.target_url or not payload.target_url.startswith(("http://", "https://")):

        raise HTTPException(
            status_code=400,
            detail="target_url deve ser uma URL válida, iniciando com http:// ou https://."
        )

    resultado = atualizar_link_cartao(
        card_code=card_code,
        owner_id=current_user.id,
        target_url=payload.target_url
    )

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para editar este cartão."
        )

    return {
        "message": "Link do cartão atualizado com sucesso!",
        "card_code": resultado["card_code"],
        "target_url": resultado["target_url"]
    }
