"""
Cliente de baixo nível para a API do Notion.

Responsabilidade única: falar com a API do Notion (via SDK oficial
`notion-client`). Não conhece a tabela `prospeccao`, não conhece
Postgres, não faz mapeamento de negócio — isso é papel do
notion_service.py.
"""

from typing import Any, Dict, List, Optional

from notion_client import Client

from app.integrations.notion import config


class NotionClient:
    """Wrapper fino sobre o SDK oficial do Notion."""

    def __init__(self) -> None:

        if not config.NOTION_TOKEN:
            raise RuntimeError(
                "NOTION_TOKEN não encontrado no .env. "
                "Crie uma integração em https://www.notion.so/my-integrations "
                "e adicione o token no .env do projeto."
            )

        self._client = Client(auth=config.NOTION_TOKEN)

    # =====================================================
    # BUSCA (usada para localizar página-pai na 1ª execução)
    # =====================================================

    def search_pages(self, query: str = "") -> List[Dict[str, Any]]:
        """
        Retorna páginas (não databases) que foram compartilhadas
        manualmente com a integração no Notion.

        Isso é necessário porque a API do Notion não permite criar uma
        página raiz no workspace: só é possível criar conteúdo dentro
        de páginas já compartilhadas explicitamente com a integração.
        """

        resultado = self._client.search(
            query=query,
            filter={"property": "object", "value": "page"},
        )

        return resultado.get("results", [])

    # =====================================================
    # DATABASE
    # =====================================================

    def retrieve_database(self, database_id: str) -> Dict[str, Any]:
        return self._client.databases.retrieve(database_id=database_id)

    def create_database(
        self,
        parent_page_id: str,
        title: str,
        properties: Dict[str, Any],
    ) -> Dict[str, Any]:

        return self._client.databases.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            title=[{"type": "text", "text": {"content": title}}],
            initial_data_source={"properties": properties},
        )

    # =====================================================
    # DATA SOURCES
    # =====================================================
    #
    # A partir da versão 2025-09-03 da API do Notion, o conceito de
    # "database" foi dividido em dois:
    #   - Database: o container (o que aparece na sidebar do Notion)
    #   - Data Source: a tabela/schema em si, onde as páginas (linhas)
    #     realmente vivem.
    #
    # Toda consulta e criação de página passa a exigir o data_source_id,
    # não mais o database_id. O database_id continua existindo, mas só
    # serve para identificar o container.

    def extrair_data_source_id(self, database: Dict[str, Any]) -> str:
        """
        Extrai o ID do primeiro data source de uma Database.

        Uma Database recém-criada por esta integração sempre tem
        exatamente um data source (o schema definido na criação).
        """

        data_sources = database.get("data_sources") or []

        if not data_sources:
            raise RuntimeError(
                f"A Database {database.get('id')} não retornou nenhum "
                "data source. Verifique se ela não foi corrompida/excluída "
                "no Notion."
            )

        return data_sources[0]["id"]

    def query_data_source(
        self,
        data_source_id: str,
        filter_: Optional[Dict[str, Any]] = None,
        start_cursor: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        kwargs: Dict[str, Any] = {"data_source_id": data_source_id}

        if filter_:
            kwargs["filter"] = filter_

        if start_cursor:
            kwargs["start_cursor"] = start_cursor

        resultado = self._client.data_sources.query(**kwargs)

        return resultado.get("results", [])

    def query_data_source_all(
        self,
        data_source_id: str,
        filter_: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retorna TODAS as páginas de um data source, seguindo a
        paginação da API do Notion (que devolve no máximo 100 por vez).
        """

        todas: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        while True:

            kwargs: Dict[str, Any] = {"data_source_id": data_source_id}

            if filter_:
                kwargs["filter"] = filter_

            if cursor:
                kwargs["start_cursor"] = cursor

            resposta = self._client.data_sources.query(**kwargs)

            todas.extend(resposta.get("results", []))

            if not resposta.get("has_more"):
                break

            cursor = resposta.get("next_cursor")

        return todas

    # =====================================================
    # PÁGINAS (REGISTROS DENTRO DO DATA SOURCE)
    # =====================================================

    def create_page(
        self,
        data_source_id: str,
        properties: Dict[str, Any],
    ) -> Dict[str, Any]:

        return self._client.pages.create(
            parent={"type": "data_source_id", "data_source_id": data_source_id},
            properties=properties,
        )

    def update_page(
        self,
        page_id: str,
        properties: Dict[str, Any],
    ) -> Dict[str, Any]:

        return self._client.pages.update(
            page_id=page_id,
            properties=properties,
        )

    def find_page_by_cpf(
        self,
        data_source_id: str,
        cpf: str,
    ) -> Optional[Dict[str, Any]]:

        resultados = self.query_data_source(
            data_source_id=data_source_id,
            filter_={
                "property": "CPF",
                "rich_text": {"equals": cpf},
            },
        )

        return resultados[0] if resultados else None