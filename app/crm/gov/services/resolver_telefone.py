from app.crm.gov.models.cliente import Cliente


def resolver_telefone(repo, cpf, final_gov):

    cpf = str(cpf)

    for linha in repo.listar_clientes():

        cpf_cliente = linha[1]

        if not cpf_cliente:
            continue

        if str(cpf_cliente) != cpf:
            continue

        telefones = linha[9]

        if not telefones:
            return None

        lista = [
            telefone.strip()
            for telefone in str(telefones).split(";")
        ]

        telefone_assertivo = None

        for telefone in lista:

            numeros = "".join(
                filter(str.isdigit, telefone)
            )

            if numeros.endswith(final_gov):

                telefone_assertivo = telefone
                break

        if telefone_assertivo is None:
            return None

        return Cliente(

            cpf=str(cpf_cliente),

            nome=linha[0],

            telefone=telefone_assertivo,

            cidade=linha[7],

            uf=linha[8],

            categoria=linha[5],

            posto=linha[6]

        )

    return None