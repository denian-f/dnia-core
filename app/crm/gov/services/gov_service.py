from app.database.repository import PostgresRepository


def proximo_cliente():

    repo = PostgresRepository()

    try:

        clientes = repo.clientes_pendentes()

    finally:

        repo.fechar()

    if not clientes:
        return None

    return clientes[0]


def iniciar_fluxo_gov(phone: str):

    # Import local para evitar importação circular
    from app.services.gov.handler import iniciar_validacao

    cliente = proximo_cliente()

    if not cliente:

        return (
            "🎉 Processo concluído!\n\n"
            "Não existem clientes pendentes."
        )

    iniciar_validacao(
        phone=phone,
        linha=cliente["linha"],
        cpf=cliente["cpf"],
        nome=cliente["nome"]
    )

    return None