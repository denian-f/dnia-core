from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.config import VERIFY_TOKEN
from app.whatsapp.parser import parse_message
from app.whatsapp.sender import send_text_message

from app.services.assistant import chat
from app.services.router import route_message
from app.services.menu import get_main_menu
from app.services.dispatcher import dispatch

from app.security.password import validate_password
from app.security.totp import verify_totp

from app.state.manager import (
    get_state,
    set_state,
    clear_state
)

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

    if not message:
        print("Evento recebido, mas não é uma mensagem.")
        return {"status": "received"}

    state = get_state(message["telefone"])

    # ==================================================
    # Usuário já está dentro dos serviços do DNIA Core
    # ==================================================

    if state and state["state"] in [
        "WAITING_MENU_OPTION",
        "WAITING_CATALOG_CITY",
        "WAITING_GOV_DIGITS"
    ]:

        resposta = dispatch(
        phone=message["telefone"],
        message=message["mensagem"]
    )

        if isinstance(resposta, dict):

            if resposta.get("message"):

                send_text_message(
                    to=message["telefone"],
                    message=resposta["message"]
                )

            if resposta.get("show_menu"):

                from app.services.menu import enviar_menu

                enviar_menu(message["telefone"])

                return

            proximo = resposta.get("next_client")

            if proximo:

                from app.services.gov.handler import iniciar_validacao

                iniciar_validacao(
                    phone=message["telefone"],
                    linha=proximo["linha"],
                    cpf=proximo["cpf"],
                    nome=proximo["nome"]
                )

            else:

                send_text_message(
                    to=message["telefone"],
                    message=(
                        "🎉 Processo concluído!\n\n"
                        "Não existem mais clientes pendentes."
                    )
                )

        elif resposta:

            send_text_message(
                to=message["telefone"],
                message=resposta
            )

        return {"status": "received"}

    # ==================================================
    # Fluxos de autenticação
    # ==================================================

    if state:

        current_state = state["state"]

        if current_state == "WAITING_PASSWORD":

            if validate_password(message["mensagem"]):

                set_state(
                    phone=message["telefone"],
                    state="WAITING_TOTP"
                )

                resposta = (
                    "✅ Senha correta!\n\n"
                    "Agora informe o código de autenticação (2FA)."
                )

            else:

                resposta = (
                    "❌ Senha incorreta.\n\n"
                    "Tente novamente."
                )

            send_text_message(
                to=message["telefone"],
                message=resposta
            )

            return {"status": "received"}

        elif current_state == "WAITING_TOTP":

            if verify_totp(message["mensagem"]):

                set_state(
                    phone=message["telefone"],
                    state="WAITING_MENU_OPTION",
                    data={
                        "authenticated": True
                    },
                    duration=timedelta(minutes=2)
                )

                resposta = (
                    "✅ Código válido!\n\n"
                    "Sessão autenticada por 2 minutos. 🚀"
                )

                send_text_message(
                    to=message["telefone"],
                    message=resposta
                )

                send_text_message(
                    to=message["telefone"],
                    message=get_main_menu()
                )

            else:

                resposta = (
                    "❌ Código inválido.\n\n"
                    "Tente novamente."
                )

                send_text_message(
                    to=message["telefone"],
                    message=resposta
                )

            return {"status": "received"}

    # ==================================================
    # Fluxo normal
    # ==================================================

    route = route_message(
        phone=message["telefone"],
        message=message["mensagem"]
    )

    print("\n========== NOVA MENSAGEM ==========\n")
    print(f"Nome: {message['nome']}")
    print(f"Telefone: {message['telefone']}")
    print(f"Mensagem: {message['mensagem']}")
    print(f"Tipo: {message['tipo']}")
    print("===================================\n")

    if not route["protected"]:

        resposta = chat(message["mensagem"])

    elif not route["authenticated"]:

        resposta = (
            "🔒 Você não possui autorização para acessar esse recurso."
        )

    elif route["requires_password"]:

        set_state(
            phone=message["telefone"],
            state="WAITING_PASSWORD"
        )

        resposta = (
            "🔑 Área protegida.\n\n"
            "Digite sua senha para continuar."
        )

    else:

        resposta = chat(message["mensagem"])

    send_text_message(
        to=message["telefone"],
        message=resposta
    )

    return {"status": "received"}