from datetime import datetime, timedelta

# Armazena os estados das conversas em memória
conversation_states = {}

# Duração padrão dos estados
DEFAULT_DURATION = timedelta(minutes=5)


def set_state(
    phone: str,
    state: str,
    data: dict | None = None,
    duration: timedelta | None = None
):
    """
    Define o estado atual de um usuário.

    Args:
        phone: Número do usuário.
        state: Nome do estado.
        data: Dados extras do estado.
        duration: Tempo de duração do estado.
    """

    conversation_states[phone] = {
        "state": state,
        "data": data or {},
        "created_at": datetime.now(),
        "duration": duration or DEFAULT_DURATION
    }


def get_state(phone: str):
    """
    Retorna o estado atual do usuário.
    Remove automaticamente estados expirados.
    """

    state = conversation_states.get(phone)

    if not state:
        return None

    if datetime.now() - state["created_at"] > state["duration"]:

        conversation_states.pop(phone, None)

        return None

    return state


def clear_state(phone: str):
    """
    Remove o estado do usuário.
    """

    conversation_states.pop(phone, None)