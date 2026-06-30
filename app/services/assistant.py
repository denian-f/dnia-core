from app.ai.provider import generate_response


def chat(user_message: str) -> str:
    """
    Recebe a mensagem do usuário e retorna a resposta da IA.
    """

    response = generate_response(user_message)

    return response