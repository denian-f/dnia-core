"""
Orquestrador da sincronização PostgreSQL -> Notion.

Fluxo (unidirecional, por enquanto):
    1. Conecta ao Postgres via PostgresRepository (já existente, não alterado).
    2. Conecta ao Notion via NotionClient.
    3. Garante que a Database "CRM Prospecção" existe (cria na 1ª execução).
    4. Busca todos os registros de `prospeccao` e faz upsert por CPF.
    5. Exibe um resumo (encontrados / criados / atualizados / ignorados).

Execução:
    python -m app.integrations.notion.sync

O código já está estruturado para permitir, futuramente, sincronização
bidirecional (Notion -> Postgres): bastaria adicionar um método
`importar_do_notion()` neste mesmo orquestrador, reaproveitando
NotionService e PostgresRepository, sem alterar o fluxo atual.
"""

from app.database.repository import PostgresRepository
from app.integrations.notion import config
from app.integrations.notion.notion_client import NotionClient
from app.integrations.notion.notion_service import (
    NotionService,
    ProspeccaoRecord,
    SyncAction,
)


def sync_prospeccao() -> dict:
    """
    Sincroniza a tabela `prospeccao`.

    Se NOTION_BIDIRECIONAL estiver ligado (padrão), a ordem é:

      1. Notion -> Postgres: importa edições manuais feitas no painel
         do Notion (status, observações, etc.) para o banco oficial.
      2. Postgres -> Notion: exporta o estado atual do Postgres de
         volta pro Notion (upsert por CPF, sem duplicar).

    Fazer a importação ANTES da exportação, na mesma execução, evita
    que uma edição feita no Notion seja sobrescrita por um valor antigo
    vindo do Postgres.
    """

    repositorio = PostgresRepository()
    servico_notion = NotionService(NotionClient())

    resumo = {
        "importados_notion": 0,
        "atualizados_no_postgres": 0,
        "encontrados": 0,
        "criados": 0,
        "atualizados": 0,
        "ignorados": 0,
    }

    try:
        servico_notion.ensure_database()

        if config.NOTION_BIDIRECIONAL:
            try:
                resumo_import = servico_notion.importar_do_notion(repositorio)
                resumo["importados_notion"] = resumo_import["processados"]
                resumo["atualizados_no_postgres"] = resumo_import["atualizados"]
            except Exception as erro:
                # A importação é best-effort: se falhar, seguimos com a
                # exportação normal em vez de travar a sincronização inteira.
                print(f"Aviso: falha ao importar edições do Notion: {erro}")

        linhas = repositorio.listar_prospeccao()
        resumo["encontrados"] = len(linhas)

        for linha in linhas:

            registro = ProspeccaoRecord.from_row(linha)

            try:
                acao = servico_notion.upsert(registro)
            except Exception as erro:
                print(f"Erro ao sincronizar CPF {registro.cpf}: {erro}")
                resumo["ignorados"] += 1
                continue

            if acao == SyncAction.CRIADO:
                resumo["criados"] += 1
            elif acao == SyncAction.ATUALIZADO:
                resumo["atualizados"] += 1
            else:
                resumo["ignorados"] += 1

    finally:
        repositorio.fechar()

    return resumo


def _exibir_resumo(resumo: dict) -> None:

    print("\n=== Sincronização PostgreSQL <-> Notion concluída ===")

    if config.NOTION_BIDIRECIONAL:
        print(f"Páginas lidas do Notion   : {resumo['importados_notion']}")
        print(f"Atualizados no Postgres   : {resumo['atualizados_no_postgres']}")
        print("-")

    print(f"Total encontrados : {resumo['encontrados']}")
    print(f"Total criados     : {resumo['criados']}")
    print(f"Total atualizados : {resumo['atualizados']}")
    print(f"Total ignorados   : {resumo['ignorados']}")


def main() -> None:
    resumo = sync_prospeccao()
    _exibir_resumo(resumo)


if __name__ == "__main__":
    main()