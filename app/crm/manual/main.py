"""
Importação manual de clientes a partir de arquivos HTML salvos em disco.

Uso:
    python -m app.crm.manual.main

Fluxo:
    Arquivo HTML -> parser.extrair_cliente -> ManualRunner
        -> CRMExporter -> PostgresRepository -> PostgreSQL

Nenhuma dependência de Playwright ou de automação de navegador.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

from app.crm.manual.parser import extrair_cliente
from app.crm.manual.runner import ManualRunner

BASE_DIR: Final[Path] = Path(__file__).resolve().parent
ENTRADA_DIR: Final[Path] = BASE_DIR / "entrada"
PROCESSADOS_DIR: Final[Path] = BASE_DIR / "processados"
ERRO_DIR: Final[Path] = BASE_DIR / "erro"

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _garantir_pastas() -> None:

    for pasta in (ENTRADA_DIR, PROCESSADOS_DIR, ERRO_DIR):
        pasta.mkdir(parents=True, exist_ok=True)


def _mover(arquivo: Path, destino_dir: Path) -> None:

    destino = destino_dir / arquivo.name

    if destino.exists():
        destino.unlink()

    arquivo.rename(destino)


def _processar_arquivo(arquivo: Path, runner: ManualRunner) -> bool:

    print()
    print("=" * 48)
    print("Arquivo:")
    print(arquivo.name)
    print()

    try:

        html = arquivo.read_text(encoding="utf-8", errors="ignore")

        cliente = extrair_cliente(html)

        runner.processar(cliente)

        print("Cliente:")
        print(cliente.nome)
        print()
        print("CPF:")
        print(cliente.cpf)
        print()
        print("Status:")
        print("Importado")
        print("=" * 48)

        _mover(arquivo, PROCESSADOS_DIR)

        return True

    except Exception as erro:

        print("Status:")
        print(f"Erro: {erro}")
        print("=" * 48)

        logger.debug("Falha ao processar %s", arquivo.name, exc_info=True)

        _mover(arquivo, ERRO_DIR)

        return False


def main() -> None:

    _garantir_pastas()

    arquivos = sorted(ENTRADA_DIR.glob("*.html"))

    runner = ManualRunner()

    importados = 0
    erros = 0

    try:

        for arquivo in arquivos:

            if _processar_arquivo(arquivo, runner):
                importados += 1
            else:
                erros += 1

    finally:

        runner.finalizar()

    print()
    print("=" * 30)
    print("Arquivos encontrados:")
    print(len(arquivos))
    print()
    print("Importados:")
    print(importados)
    print()
    print("Erros:")
    print(erros)
    print("=" * 30)


if __name__ == "__main__":
    main()
