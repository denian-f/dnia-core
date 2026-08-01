import requests

from app.dna_connect.email import config

BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"


def enviar_email(
    destinatario: str,
    assunto: str,
    conteudo_html: str,
    conteudo_texto: str = None
):
    """
    Envia um e-mail transacional através da API HTTP da Brevo.

    Camada isolada de integração externa: nunca lança exceção para o
    chamador (falhas de rede, timeout ou erro HTTP da Brevo são sempre
    convertidas num dict de status controlado), e nunca expõe a
    BREVO_API_KEY em nenhum retorno.
    """

    if not config.BREVO_API_KEY:
        return {"status": "failed", "error": "Serviço de e-mail não configurado."}

    payload = {
        "sender": {
            "name": config.EMAIL_FROM_NAME,
            "email": config.EMAIL_FROM_ADDRESS
        },
        "to": [{"email": destinatario}],
        "subject": assunto,
        "htmlContent": conteudo_html
    }

    if conteudo_texto:
        payload["textContent"] = conteudo_texto

    headers = {
        "accept": "application/json",
        "api-key": config.BREVO_API_KEY,
        "content-type": "application/json"
    }

    try:

        response = requests.post(
            BREVO_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=15
        )

    except requests.RequestException:

        return {
            "status": "failed",
            "error": "Falha de comunicação com o serviço de e-mail."
        }

    if response.status_code >= 400:

        return {
            "status": "failed",
            "error": f"Serviço de e-mail retornou erro ({response.status_code})."
        }

    try:
        corpo = response.json()
    except ValueError:
        corpo = {}

    return {"status": "sent", "message_id": corpo.get("messageId")}
