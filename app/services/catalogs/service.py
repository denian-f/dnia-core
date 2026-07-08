from app.services.catalogs.handler import handle_catalog


def catalog_service(phone: str, message: str):
    """
    Serviço principal do módulo de catálogos.
    """

    return handle_catalog(
        phone=phone,
        message=message
    )