import requests

from app.config import (
    AIRTABLE_TOKEN,
    AIRTABLE_BASE_ID
)

TABLE_PRODUCTS = "Product"
TABLE_IMAGES = "Imagens"

def buscar_produtos_por_cidade(cidade: str):

    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/{TABLE_PRODUCTS}"
    )

    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}"
    }

    params = {
        "filterByFormula": f"{{cidade}} = '{cidade}'"
    }

    produtos = []

    while url:

        response = requests.get(
            url,
            headers=headers,
            params=params
        )

        if response.status_code != 200:
            raise Exception(response.text)

        data = response.json()

        for record in data.get("records", []):

            fields = record.get("fields", {})

            imagem = None

            if (
                isinstance(fields.get("Imagem"), list)
                and fields["Imagem"]
            ):
                imagem = fields["Imagem"][0]["url"]

            produtos.append({

                "codigo": fields.get("codigo"),

                "preco": fields.get("preco"),

                "linha": fields.get("linha do produto"),

                "imagem": imagem

            })

        offset = data.get("offset")

        if offset:

            url = (
                f"https://api.airtable.com/v0/"
                f"{AIRTABLE_BASE_ID}/{TABLE_PRODUCTS}"
                f"?offset={offset}"
            )

            params = None

        else:

            url = None

    return produtos

def buscar_background_por_cidade(cidade: str):

    url = (
        f"https://api.airtable.com/v0/"
        f"{AIRTABLE_BASE_ID}/{TABLE_IMAGES}"
    )

    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}"
    }

    response = requests.get(
        url,
        headers=headers
    )

    if response.status_code != 200:
        raise Exception(response.text)

    data = response.json()

    fallback = None

    for record in data.get("records", []):

        fields = record.get("fields", {})

        nome = fields.get("Name")

        anexos = fields.get("Attachments")

        if not anexos:
            continue

        imagem = anexos[0]["url"]

        if nome and nome.lower() == "background":
            fallback = imagem

        if (
            nome
            and nome.strip().lower()
            == cidade.strip().lower()
        ):
            return imagem

    return fallback