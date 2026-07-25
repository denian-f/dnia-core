from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.cards.service import resolve_target_url, ativar_cartao

router = APIRouter()


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
async def activate_card(request: Request):
    """
    Ativa um cartão, associando-o a um usuário (existente ou novo).
    """

    data = await request.json()

    name = data.get("name")
    email = data.get("email")
    card_code = data.get("card_code")

    if not name or not email or not card_code:

        raise HTTPException(
            status_code=400,
            detail="Campos obrigatórios: name, email, card_code."
        )

    resultado = ativar_cartao(
        name=name,
        email=email,
        card_code=card_code
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
