from app.database.repository import PostgresRepository

from app.services.gov.handler import iniciar_validacao


def iniciar_fluxo_gov(phone: str):

    repo = PostgresRepository()

    try:

        clientes = repo.clientes_pendentes()

    finally:

        repo.fechar()

    if not clientes:

        return (
            "✅ Não existem clientes pendentes para validação."
        )

    cliente = clientes[0]

    iniciar_validacao(
        phone=phone,
        linha=cliente["linha"],
        cpf=cliente["cpf"],
        nome=cliente["nome"]
    )

    # A própria função iniciar_validacao() já envia
    # a mensagem para o WhatsApp, então não precisamos
    # retornar nenhuma resposta ao webhook.

    return None