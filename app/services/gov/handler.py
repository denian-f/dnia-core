from datetime import timedelta

from app.state.manager import (
    set_state,
    get_state,
    clear_state,
)

from app.whatsapp.sender import send_text_message

from app.crm.gov.services.validacao import processar_validacao
from app.crm.gov.services.gov_service import proximo_cliente


def iniciar_validacao(
    phone: str,
    linha: int,
    cpf: str,
    nome: str,
):
    """
    Inicia uma validação GOV via WhatsApp.
    """

    set_state(
        phone=phone,
        state="WAITING_GOV_DIGITS",
        data={
            "linha": linha,
            "cpf": cpf,
            "nome": nome,
        },
        duration=timedelta(minutes=30)
    )

    mensagem = (
        "🪪 *Validação GOV*\n\n"
        f"Cliente: {nome}\n"
        f"CPF: {cpf}\n\n"
        "Digite os *2 últimos dígitos* do telefone."
    )

    send_text_message(
        to=phone,
        message=mensagem
    )


def handle_gov(phone: str, message: str):
    """
    Processa a resposta da validação GOV.
    """

    state = get_state(phone)

    if not state:
        return (
            "❌ Nenhuma validação GOV está em andamento."
        )

    dados = state["data"]

    linha = dados["linha"]
    cpf = dados["cpf"]

    digitos = message.strip()

    if len(digitos) != 2 or not digitos.isdigit():
        return (
            "❌ Valor inválido.\n\n"
            "Informe exatamente os 2 últimos dígitos."
        )

    cliente = processar_validacao(
        linha=linha,
        cpf=cpf,
        digitos=digitos
    )

    clear_state(phone)

    if not cliente:

        return (
            "⚠️ Nenhum telefone correspondente foi encontrado."
        )

    resposta = (
        "✅ Cliente validado!\n\n"
        f"Nome: {cliente.nome}\n"
        f"Telefone: {cliente.telefone}"
    )

    proximo = proximo_cliente()

    if proximo:

        iniciar_validacao(
            phone=phone,
            linha=proximo["linha"],
            cpf=proximo["cpf"],
            nome=proximo["nome"]
        )

    else:

        send_text_message(
            to=phone,
            message=(
                "🎉 Processo concluído!\n\n"
                "Não existem mais clientes pendentes."
            )
        )

    return resposta