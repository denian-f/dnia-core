"""
Monta o link clicável do WhatsApp (wa.me) a partir de nome e telefone.

Responsabilidade única: só transforma texto, sem depender do Postgres
nem da API do Notion. Usado por notion_service.py para preencher a
propriedade "WhatsApp" no upsert Postgres -> Notion.
"""

import re
from typing import Optional
from urllib.parse import quote

_DDI_BRASIL = "55"


def montar_link_whatsapp(nome: Optional[str], telefone: Optional[str]) -> Optional[str]:
    """
    Retorna a URL "https://wa.me/<numero>?text=<mensagem>" pronta para
    clicar, ou None se não houver telefone válido para montar o link.
    """

    numero = _normalizar_telefone(telefone)

    if not numero:
        return None

    primeiro_nome = _primeiro_nome(nome)

    mensagem = (
        f"Olá, estou falando com {primeiro_nome}?" if primeiro_nome else "Olá!"
    )

    return f"https://wa.me/{numero}?text={quote(mensagem)}"


def _normalizar_telefone(telefone: Optional[str]) -> Optional[str]:
    """
    Remove tudo que não for dígito e garante o DDI 55 na frente.

    (12) 98121-5934 -> 5512981215934

    Números que já vierem com o 55 na frente (12/13 dígitos) são
    mantidos como estão, para não duplicar o DDI.
    """

    if not telefone:
        return None

    digitos = re.sub(r"\D", "", telefone)

    if len(digitos) in (10, 11):
        return _DDI_BRASIL + digitos

    if len(digitos) in (12, 13) and digitos.startswith(_DDI_BRASIL):
        return digitos

    return None


def _primeiro_nome(nome: Optional[str]) -> str:
    """
    Extrai o primeiro nome e normaliza para apenas a primeira letra
    maiúscula, preservando acentos.

    LUIS GUILHERME CUNHA FEITOSA -> Luis
    José Carlos Silva -> José
    """

    if not nome or not nome.strip():
        return ""

    primeiro = nome.strip().split()[0]

    return primeiro.capitalize()
