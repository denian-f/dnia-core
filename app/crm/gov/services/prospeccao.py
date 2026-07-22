from datetime import datetime


def adicionar_prospeccao(repo, cliente):

    for linha in repo.listar_prospeccao():

        cpf_existente = linha[0]

        if str(cpf_existente) == cliente.cpf:
            return

    repo.adicionar_prospeccao(cliente)

    print("Cliente enviado para Prospecção.")