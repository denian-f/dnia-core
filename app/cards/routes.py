from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.cards.service import resolve_target_url

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
