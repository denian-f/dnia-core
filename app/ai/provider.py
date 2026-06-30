from groq import Groq

from app.config import GROQ_API_KEY
from app.ai.prompts import SYSTEM_PROMPT

client = Groq(api_key=GROQ_API_KEY)


def generate_response(user_message: str) -> str:
    """
    Envia a mensagem para o Groq e retorna apenas o texto da resposta.
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        temperature=0.7,
        max_tokens=1024,
    )

    return response.choices[0].message.content