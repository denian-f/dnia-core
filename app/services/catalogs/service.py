from app.services.catalogs.handler import handle_catalog

from app.services.catalogs.airtable import (
    buscar_produtos_por_cidade,
    buscar_background_por_cidade
)


def catalog_service(phone: str, message: str):
    """
    Serviço principal do módulo de catálogos.
    """

    return handle_catalog(
        phone=phone,
        message=message
    )


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

    return {

        "success": True,

        "cidade": cidade,

        "background": background,

        "produtos": produtos

    }