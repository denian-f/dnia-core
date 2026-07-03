from datetime import datetime, timedelta

# Armazena o estado das conversas em memória
conversation_states = {}


def set_state(phone: str, state: str, data: dict | None = None):
    """
    Define o estado atual de um usuário.
    """

    conversation_states[phone] = {
        "state": state,
        "data": data or {},
        "created_at": datetime.now()
    }


def get_state(phone: str):
    """
    Retorna o estado atual do usuário.
    """

    state = conversation_states.get(phone)

    if not state:
        return None

    # Expira automaticamente após 5 minutos
    if datetime.now() - state["created_at"] > timedelta(minutes=5):

        conversation_states.pop(phone)

        return None

    return state


def clear_state(phone: str):
    """
    Remove o estado do usuário.
    """

    conversation_states.pop(phone, None)