"""
Parser de HTML da página de cliente (ConsigBR).

Recebe apenas uma string HTML — não depende de Playwright nem de
qualquer outra forma de automação de navegador. A origem do HTML
(arquivo, clipboard, API etc.) é irrelevante para este módulo.

Reaproveita os seletores CSS de app.crm.collector.selectors.sistema
e as funções de formatação de app.crm.collector.parser.formatter,
que já eram independentes de Playwright.
"""

from __future__ import annotations

import re
from typing import List, Optional

from bs4 import BeautifulSoup
from bs4.element import Tag

_MATRICULA_SCRIPT_RE = re.compile(r"matricula\s*=\s*\"(\d+)\"")

from app.crm.collector.models.cliente import Cliente
from app.crm.collector.models.contrato import Contrato
from app.crm.collector.parser.formatter import (
    extrair_data,
    extrair_idade,
    separar_cidade_uf,
)
from app.crm.collector.selectors import sistema


class ParserError(Exception):
    """Erro ao extrair os dados do cliente a partir do HTML."""


def extrair_cliente(html: str) -> Cliente:

    soup = BeautifulSoup(html, "html.parser")

    nome = _texto(soup.select_one(sistema.NOME))
    cpf = _texto(soup.select_one(sistema.CPF))

    if not nome or not cpf:
        raise ParserError(
            "Não foi possível localizar Nome/CPF no HTML informado."
        )

    matricula = _matricula(soup)
    posto = _texto(soup.select_one(sistema.POSTO))

    cidade_raw = _valor_campo(soup, "Cidade")
    nascimento_raw = _valor_campo(soup, "Nasc")
    categoria = _valor_campo(soup, "Categoria")

    idade = extrair_idade(nascimento_raw)
    nascimento = extrair_data(nascimento_raw)
    cidade, uf = separar_cidade_uf(cidade_raw)

    cliente = Cliente(
        nome=nome,
        nascimento=nascimento,
        idade=idade,
        cpf=cpf,
        matricula=matricula,
        categoria=categoria,
        posto=posto,
        cidade=cidade,
        uf=uf,
    )

    cliente.telefones = _extrair_telefones(soup)
    cliente.contratos = _extrair_contratos(soup)

    return cliente


def _normalizar_espacos(texto: str) -> str:

    # Ao contrário do inner_text() de um navegador, BeautifulSoup não
    # colapsa espaços/quebras de linha do HTML de origem. Normalizamos
    # aqui para o parser ser tolerante a indentação e formatação do
    # arquivo salvo manualmente.
    return " ".join(texto.split())


def _texto(tag: Optional[Tag]) -> str:

    return _normalizar_espacos(tag.get_text()) if tag else ""


def _matricula(soup: BeautifulSoup) -> str:

    # O toggle de LGPD do sistema mascara o <span class="beneficio"> via
    # JavaScript client-side; o valor real fica sempre embutido, sem máscara,
    # dentro do próprio <script> inline (função atualizaLgpd), então é a
    # fonte confiável independente do estado do toggle no momento do save.
    for script in soup.find_all("script"):

        texto_script = script.string or script.get_text()

        if not texto_script:
            continue

        match = _MATRICULA_SCRIPT_RE.search(texto_script)

        if match:
            return match.group(1)

    return _texto(soup.select_one(sistema.MATRICULA))


def _valor_campo(soup: BeautifulSoup, campo: str) -> str:

    # Equivalente a page.locator(f"td:has-text('{campo}')") do Playwright:
    # não existe pseudo-seletor ":has-text" em CSS/soupsieve, então
    # percorremos os <td> procurando o texto e lendo o <span> interno.
    for td in soup.find_all("td"):

        if campo in td.get_text():

            span = td.find("span")

            if span:
                return _normalizar_espacos(span.get_text())

    return ""


def _extrair_telefones(soup: BeautifulSoup) -> List[str]:

    telefones = []

    for elemento in soup.select(sistema.TELEFONES):

        numero = _normalizar_espacos(elemento.get_text())

        if numero:
            telefones.append(numero)

    return telefones


def _extrair_contratos(soup: BeautifulSoup) -> List[Contrato]:

    return [_extrair_contrato(linha) for linha in soup.select(sistema.CONTRATOS)]


def _extrair_contrato(linha: Tag) -> Contrato:

    img = linha.find("img")
    banco = img.get("alt", "") if img else ""

    contrato = ""
    tds = linha.find_all("td")

    if len(tds) > 1:

        span = tds[1].find("span")

        if span:
            contrato = _normalizar_espacos(span.get_text())

    parcela = _input_value(linha, "vl_parcela")
    prazo = _input_value(linha, "valida_prazo")
    taxa = _input_value(linha, "valida_taxa")
    quitacao = _input_value(linha, "vl_quitacao")

    valor_liberado_tag = linha.select_one("td[id^='vl_liberado']")

    valor_liberado = (
        _normalizar_espacos(
            valor_liberado_tag.get_text().replace("R$", "").replace("\xa0", " ")
        )
        if valor_liberado_tag
        else ""
    )

    return Contrato(
        banco=banco,
        contrato=contrato,
        parcela=parcela,
        prazo=prazo,
        taxa=taxa,
        valor_liberado=valor_liberado,
        quitacao=quitacao,
    )


def _input_value(linha: Tag, prefixo_id: str) -> str:

    tag = linha.select_one(f"input[id^='{prefixo_id}']")

    return _normalizar_espacos(tag.get("value", "")) if tag else ""
