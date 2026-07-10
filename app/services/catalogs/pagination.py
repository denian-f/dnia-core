from math import ceil


PRODUTOS_POR_PAGINA = 9


def montar_paginas(produtos: list):
    """
    Organiza os produtos em páginas de 9 itens.
    """

    paginas = []

    total_paginas = ceil(
        len(produtos) / PRODUTOS_POR_PAGINA
    )

    for pagina_atual in range(total_paginas):

        inicio = pagina_atual * PRODUTOS_POR_PAGINA

        fim = inicio + PRODUTOS_POR_PAGINA

        produtos_pagina = produtos[inicio:fim]

        pagina = {}

        # Linha (subtítulo da página)

        pagina["linha"] = (
            produtos_pagina[0]["linha"]
            if produtos_pagina
            else ""
        )

        # Produtos

        for indice in range(9):

            chave = indice + 1

            if indice < len(produtos_pagina):

                produto = produtos_pagina[indice]

                pagina[f"p{chave}_img"] = produto["imagem"]

                pagina[f"p{chave}_cod"] = produto["codigo"]

                pagina[f"p{chave}_preco"] = produto["preco"]

            else:

                pagina[f"p{chave}_img"] = None

                pagina[f"p{chave}_cod"] = ""

                pagina[f"p{chave}_preco"] = ""

        paginas.append(pagina)

    return paginas