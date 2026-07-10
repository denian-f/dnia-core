from app.services.catalogs.airtable import (
    buscar_produtos_por_cidade,
    buscar_background_por_cidade
)

from app.services.catalogs.pdf import gerar_pdf
from app.services.catalogs.pagination import montar_paginas
from app.services.catalogs.templates import render_catalog_template


def gerar_catalogo(cidade: str):
    """
    Busca todas as informações necessárias
    para gerar um catálogo.
    """

    produtos = buscar_produtos_por_cidade(cidade)

    if not produtos:

        return {
            "success": False,
            "message": (
                f"❌ Nenhum produto encontrado para '{cidade}'."
            )
        }

    background = buscar_background_por_cidade(cidade)

    paginas = montar_paginas(produtos)

    html = render_catalog_template(
        cidade=cidade,
        paginas=paginas,
        background=background
    )

    pdf = gerar_pdf(
        html=html,
        cidade=cidade
    )

    return {
        "success": True,
        "cidade": cidade,
        "background": background,
        "produtos": produtos,
        "html": html,
        "pdf": pdf
    }