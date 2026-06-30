def parse_message(data: dict):
    """
    Extrai as principais informações do JSON enviado pela Meta.
    Retorna um dicionário simplificado ou None caso não seja uma mensagem.
    """

    try:
        value = (
            data["entry"][0]
            ["changes"][0]
            ["value"]
        )

        contact = value["contacts"][0]
        message = value["messages"][0]

        return {
            "nome": contact["profile"]["name"],
            "telefone": message["from"],
            "mensagem": message["text"]["body"],
            "tipo": message["type"],
            "message_id": message["id"],
            "timestamp": message["timestamp"],
        }

    except (KeyError, IndexError):
        return None