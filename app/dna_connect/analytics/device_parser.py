"""
Extrai categorias amplas (tipo de dispositivo, sistema operacional,
navegador) a partir do cabeçalho User-Agent — regex simples, sem
biblioteca externa. Isso NÃO identifica um aparelho individual: é só
uma categoria ampla (ex: "mobile"/"Android"/"Chrome") — qualquer
pessoa com um aparelho parecido gera o mesmo resultado.
"""

import re

_PADRAO_MOBILE = re.compile(r"Mobi|iPhone|Android", re.IGNORECASE)
_PADRAO_TABLET = re.compile(r"iPad|Tablet", re.IGNORECASE)


def detectar_tipo_dispositivo(user_agent: str) -> str:

    if not user_agent:
        return "desconhecido"

    # iPad moderno se identifica como "Macintosh" com suporte a touch,
    # mas isso exigiria JS no cliente para detectar — no server-side,
    # cobrimos o caso comum (UA ainda contém "iPad" ou "Tablet").
    if _PADRAO_TABLET.search(user_agent) and "Mobile" not in user_agent:
        return "tablet"

    if _PADRAO_MOBILE.search(user_agent):
        return "mobile"

    return "desktop"


_SISTEMAS_OPERACIONAIS = (
    ("Windows", "Windows"),
    ("Mac OS X", "macOS"),
    ("Android", "Android"),
    ("iPhone OS", "iOS"),
    ("iPad", "iOS"),
    ("Linux", "Linux"),
)


def detectar_sistema_operacional(user_agent: str):

    if not user_agent:
        return None

    for trecho, nome in _SISTEMAS_OPERACIONAIS:

        if trecho in user_agent:
            return nome

    return None


# Ordem importa: navegadores baseados em Chromium (Edge, Opera)
# também contêm "Chrome/" no próprio User-Agent, então precisam ser
# checados antes. O mesmo vale para Chrome/Safari (Chrome também
# contém "Safari/").
_NAVEGADORES = (
    ("Edg/", "Edge"),
    ("OPR/", "Opera"),
    ("Chrome/", "Chrome"),
    ("CriOS/", "Chrome"),
    ("Firefox/", "Firefox"),
    ("FxiOS/", "Firefox"),
    ("Safari/", "Safari"),
)


def detectar_navegador(user_agent: str):

    if not user_agent:
        return None

    for trecho, nome in _NAVEGADORES:

        if trecho in user_agent:
            return nome

    return None
