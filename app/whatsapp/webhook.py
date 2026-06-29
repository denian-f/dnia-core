from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.config import VERIFY_TOKEN

router = APIRouter()


@router.get("/webhook")
async def verify_webhook(request: Request):

    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge)

    raise HTTPException(status_code=403, detail="Invalid verification token")

@router.post("/webhook")
async def receive_webhook(request: Request):

    data = await request.json()

    print(data)

    return {"status": "received"}