import os

import requests

from app.config import (
    ACCESS_TOKEN,
    PHONE_NUMBER_ID
)

def upload_document(file_path: str):
    """
    Faz upload do documento para a Meta.
    """

    url = (
        f"https://graph.facebook.com/v23.0/"
        f"{PHONE_NUMBER_ID}/media"
    )

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    with open(file_path, "rb") as arquivo:

        files = {
            "file": (
                os.path.basename(file_path),
                arquivo,
                "application/pdf"
            )
        }

        data = {
            "messaging_product": "whatsapp"
        }

        response = requests.post(
            url,
            headers=headers,
            files=files,
            data=data
        )

    response.raise_for_status()

    return response.json()["id"]

def send_document(
    to: str,
    media_id: str,
    filename: str,
):
    """
    Envia um documento do WhatsApp utilizando um Media ID.
    """

    url = (
        f"https://graph.facebook.com/v23.0/"
        f"{PHONE_NUMBER_ID}/messages"
    )

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {

        "messaging_product": "whatsapp",

        "to": to,

        "type": "document",

        "document": {

            "id": media_id,

            "filename": filename

        }

    }

    response = requests.post(
        url,
        headers=headers,
        json=payload
    )

    response.raise_for_status()

    return response.json()