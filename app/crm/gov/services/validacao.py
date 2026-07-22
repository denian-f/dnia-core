from app.database.repository import PostgresRepository

from app.crm.gov.services.resolver_telefone import resolver_telefone
from app.crm.gov.services.prospeccao import adicionar_prospeccao


def executar_validacao():

    repo = PostgresRepository()

    total = len(repo.clientes_pendentes())

    for indice, cliente_validacao in enumerate(
        repo.clientes_pendentes(),
        start=1
    ):

        linha = cliente_validacao["linha"]
        cpf = cliente_validacao["cpf"]
        nome = cliente_validacao["nome"]

        print()
        print("=" * 60)
        print(f"Cliente {indice} de {total}")
        print()
        print(f"Nome: {nome}")
        print(f"CPF : {cpf}")
        print("=" * 60)

        digitos = input(
            "Digite os 2 últimos dígitos: "
        ).strip()

        while len(digitos) != 2 or not digitos.isdigit():

            print()
            print("Valor inválido.")

            digitos = input(
                "Digite novamente: "
            ).strip()

        repo.salvar_validacao(
            linha,
            digitos
        )

        cliente = resolver_telefone(
            repo,
            cpf,
            digitos
        )

        if cliente:

            print()
            print("Cliente encontrado:")
            print(f"Nome      : {cliente.nome}")
            print(f"Telefone  : {cliente.telefone}")
            print(f"Cidade    : {cliente.cidade}")
            print(f"UF        : {cliente.uf}")
            print(f"Categoria : {cliente.categoria}")
            print(f"Posto     : {cliente.posto}")

            adicionar_prospeccao(
                repo,
                cliente
            )

        else:

            print()
            print("Nenhum telefone correspondente encontrado.")

        repo.salvar()

        print()
        print("✔ Alterações salvas.")

    repo.fechar()

    print()
    print("=" * 60)
    print("Processo finalizado.")
    print("=" * 60)

if __name__ == "__main__":
    executar_validacao()