from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.config import VERIFY_TOKEN
from app.whatsapp.parser import parse_message
from app.whatsapp.sender import send_text_message
from app.services.assistant import chat

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

    message = parse_message(data)

    if message:

        print("\n========== NOVA MENSAGEM ==========\n")
        print(f"Nome: {message['nome']}")
        print(f"Telefone: {message['telefone']}")
        print(f"Mensagem: {message['mensagem']}")
        print(f"Tipo: {message['tipo']}")
        print("===================================\n")

        resposta = chat(message["mensagem"])

        send_text_message(
            to=message["telefone"],
            message=resposta
        )

    else:

        print("Evento recebido, mas não é uma mensagem.")

    return {"status": "received"}