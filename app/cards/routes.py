from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.cards.service import resolve_target_url, ativar_cartao

router = APIRouter()


class ActivateRequest(BaseModel):

    name: str
    email: str
    card_code: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Denian Fernandes",
                "email": "denian@email.com",
                "card_code": "TESTE01"
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
def activate_card(payload: ActivateRequest):
    """
    Ativa um cartão, associando-o a um usuário (existente ou novo).
    """

    resultado = ativar_cartao(
        name=payload.name,
        email=payload.email,
        card_code=payload.card_code
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
