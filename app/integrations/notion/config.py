"""
Configuração do módulo de integração Notion <-> PostgreSQL.

Responsabilidade única: ler variáveis de ambiente relacionadas ao Notion
e persistir novas variáveis no arquivo .env quando necessário
(ex.: NOTION_DATABASE_ID gerado na primeira execução).

Não duplica nada da conexão com o Postgres — isso continua em
app/database/connection.py e app/database/config.py.
"""

import os
import re
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


# Raiz do projeto: app/integrations/notion/config.py -> sobe 3 níveis
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_PATH = PROJECT_ROOT / ".env"

if load_dotenv is not None and ENV_PATH.exists():
    # override=False: se outro módulo já carregou o .env antes, não sobrescreve.
    load_dotenv(dotenv_path=ENV_PATH, override=False)


# =====================================================
# VARIÁVEIS DE AMBIENTE
# =====================================================

NOTION_TOKEN: Optional[str] = os.getenv("NOTION_TOKEN")

NOTION_DATABASE_ID: Optional[str] = os.getenv("NOTION_DATABASE_ID")

# A partir da API do Notion 2025-09-03, toda consulta/criação de página
# usa o ID do "data source" (a tabela em si), não mais o ID da Database
# (que agora é só o container). Salvo automaticamente após a 1ª execução.
NOTION_DATA_SOURCE_ID: Optional[str] = os.getenv("NOTION_DATA_SOURCE_ID")

# Opcional: só é necessário na primeira execução, caso a busca automática
# por páginas compartilhadas com a integração não encontre nada.
NOTION_PARENT_PAGE_ID: Optional[str] = os.getenv("NOTION_PARENT_PAGE_ID")

# Nome fixo da Database criada automaticamente.
NOTION_DATABASE_TITLE = "CRM Prospecção"

# Controla se a sincronização também importa edições feitas no Notion
# de volta para o Postgres (status, observações, etc.). Default: ligado.
# Para desligar (voltar a ser só Postgres -> Notion), adicione no .env:
#   NOTION_BIDIRECIONAL=false
NOTION_BIDIRECIONAL: bool = os.getenv("NOTION_BIDIRECIONAL", "true").strip().lower() not in (
    "false",
    "0",
    "no",
    "nao",
    "não",
)


# =====================================================
# PERSISTÊNCIA NO .env
# =====================================================

def set_env_variable(key: str, value: str) -> None:
    """
    Grava (ou atualiza) uma variável no arquivo .env do projeto,
    preservando todas as demais linhas existentes.

    Usado para salvar o NOTION_DATABASE_ID após a criação automática
    da Database, para que não seja recriada nas próximas execuções.
    """

    if not ENV_PATH.exists():
        ENV_PATH.write_text(f"{key}={value}\n", encoding="utf-8")
        os.environ[key] = value
        return

    conteudo = ENV_PATH.read_text(encoding="utf-8")
    padrao = re.compile(rf"^{re.escape(key)}=.*$", flags=re.MULTILINE)

    if padrao.search(conteudo):
        novo_conteudo = padrao.sub(f"{key}={value}", conteudo)
    else:
        separador = "" if conteudo.endswith("\n") or conteudo == "" else "\n"
        novo_conteudo = f"{conteudo}{separador}{key}={value}\n"

    ENV_PATH.write_text(novo_conteudo, encoding="utf-8")

    # Atualiza também em memória, para a execução atual enxergar o valor novo.
    os.environ[key] = value


def reload() -> None:
    """Recarrega as constantes do módulo após uma escrita no .env."""

    global NOTION_DATABASE_ID, NOTION_DATA_SOURCE_ID, NOTION_PARENT_PAGE_ID

    NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
    NOTION_DATA_SOURCE_ID = os.getenv("NOTION_DATA_SOURCE_ID")
    NOTION_PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID")