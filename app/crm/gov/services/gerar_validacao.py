from app.database.repository import PostgresRepository

def gerar_validacao():

    repo = PostgresRepository()

    cpfs_prospeccao = {

        str(linha[0])

        for linha in repo.listar_prospeccao()

        if linha[0]

    }

    cpfs_validacao = {

        str(linha[0])

        for linha in repo.listar_validacao()

        if linha[0]

    }

    adicionados = 0

    for linha in repo.listar_clientes():

        nome = linha[0]
        cpf = linha[1]

        if not cpf:
            continue

        cpf = str(cpf)

        if cpf in cpfs_prospeccao:
            continue

        if cpf in cpfs_validacao:
            continue

        repo.adicionar_validacao(
            cpf,
            nome
        )

        adicionados += 1

    repo.salvar()
    repo.fechar()

    print()
    print(f"{adicionados} novos clientes adicionados para validação.")

if __name__ == "__main__":
    gerar_validacao()