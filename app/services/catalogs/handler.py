from app.state.manager import get_state, set_state

from app.services.catalogs.states import WAITING_CITY
from app.services.catalogs.service import gerar_catalogo


def handle_catalog(phone: str, message: str):
    """
    Controla a conversa do módulo de catálogos.
    """

    state = get_state(phone)

    # ==========================================
    # Primeira entrada no módulo
    # ==========================================

    if (
        not state
        or state["state"] != WAITING_CITY
    ):

        set_state(
            phone=phone,
            state=WAITING_CITY
        )

        return (
            "📄 *Gerador de Catálogos*\n\n"
            "Informe o nome da cidade."
        )

    # ==========================================
    # Cidade recebida
    # ==========================================

    cidade = message.strip()

    resultado = gerar_catalogo(cidade)

    if not resultado["success"]:

        return resultado["message"]

    quantidade = len(resultado["produtos"])

    return (
        "✅ Cidade encontrada!\n\n"
        f"📍 Cidade: *{resultado['cidade']}*\n"
        f"📦 Produtos encontrados: *{quantidade}*\n\n"
        "Na próxima etapa iremos gerar o PDF."
    )