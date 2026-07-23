"""
Camada de serviço da integração Notion.

Responsabilidade única: converter registros da tabela `prospeccao`
em propriedades do Notion, garantir que a Database exista (criando-a
na primeira execução) e fazer o upsert de cada registro usando o CPF
como chave única.

Não conhece detalhes do Postgres (isso é papel do repository) e não
conhece detalhes brutos da API do Notion (isso é papel do
notion_client.py).
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from app.integrations.notion import config
from app.integrations.notion.notion_client import NotionClient


# =====================================================
# MODELO DE DADOS
# =====================================================

@dataclass
class ProspeccaoRecord:
    """Representa uma linha da tabela `prospeccao`."""

    cpf: str
    nome: str
    telefone_assertivo: Optional[str]
    cidade: Optional[str]
    uf: Optional[str]
    categoria: Optional[str]
    posto: Optional[str]
    origem: Optional[str]
    data_cadastro: Optional[datetime]
    status: Optional[str]
    data_primeiro_contato: Optional[datetime]
    ultima_atualizacao: Optional[datetime]
    observacoes: Optional[str]
    matricula: Optional[str]

    @classmethod
    def from_row(cls, row: Tuple) -> "ProspeccaoRecord":
        """
        Constrói o record a partir da tupla retornada por
        PostgresRepository.listar_prospeccao(), cuja ordem de colunas é:

        cpf, nome, telefone_assertivo, cidade, uf, categoria, posto,
        origem, data_cadastro, status, data_primeiro_contato,
        ultima_atualizacao, observacoes, matricula
        """

        return cls(
            cpf=row[0],
            nome=row[1],
            telefone_assertivo=row[2],
            cidade=row[3],
            uf=row[4],
            categoria=row[5],
            posto=row[6],
            origem=row[7],
            data_cadastro=row[8],
            status=row[9],
            data_primeiro_contato=row[10],
            ultima_atualizacao=row[11],
            observacoes=row[12],
            matricula=row[13],
        )


class SyncAction(str, Enum):
    CRIADO = "criado"
    ATUALIZADO = "atualizado"
    IGNORADO = "ignorado"


# Schema fixo da Database criada automaticamente na primeira execução.
#
# Observação sobre "Status": a propriedade nativa do Notion do tipo
# Status exige que as opções já existam previamente (só podem ser
# criadas manualmente na UI) — ela NÃO cria opções novas ao receber um
# valor por API. Como os status vêm dinâmicos do Postgres (ex.: "NOVO",
# "NAO_RESPONDE"), usamos o tipo Select, que cria a opção
# automaticamente na primeira vez que um valor novo aparece.
_PROPRIEDADES_PADRAO: Dict[str, Any] = {
    "Nome": {"title": {}},
    "CPF": {"rich_text": {}},
    "Telefone": {"phone_number": {}},
    "Cidade": {"rich_text": {}},
    "UF": {"select": {}},
    "Categoria": {"select": {}},
    "Posto": {"select": {}},
    "Origem": {"select": {}},
    "Status": {"select": {}},
    "Observações": {"rich_text": {}},
    "Data Cadastro": {"date": {}},
    "Primeiro Contato": {"date": {}},
    "Última Atualização": {"date": {}},
    "Matrícula": {"rich_text": {}},
}


class NotionService:

    def __init__(self, client: Optional[NotionClient] = None) -> None:

        self.client = client or NotionClient()
        self.database_id: Optional[str] = config.NOTION_DATABASE_ID
        self.data_source_id: Optional[str] = config.NOTION_DATA_SOURCE_ID

    # =====================================================
    # GARANTIR QUE A DATABASE EXISTE
    # =====================================================

    def ensure_database(self) -> str:
        """
        Garante que a Database "CRM Prospecção" existe no Notion.

        - Se NOTION_DATABASE_ID já estiver no .env, reutiliza.
        - Caso contrário, localiza uma página-pai e cria a Database,
          gravando o novo ID no .env.
        """

        if self.database_id:

            if self.data_source_id:
                # Já temos tudo o que precisamos, de execuções anteriores.
                return self.data_source_id

            # Database já existia no .env, mas ainda não tínhamos o
            # data_source_id salvo (ex.: projeto criado antes desta
            # migração para a API 2025-09-03). Buscamos e persistimos.
            database = self.client.retrieve_database(self.database_id)
            data_source_id = self.client.extrair_data_source_id(database)

            config.set_env_variable("NOTION_DATA_SOURCE_ID", data_source_id)
            config.reload()
            self.data_source_id = data_source_id

            return data_source_id

        parent_page_id = self._resolver_pagina_pai()

        database = self.client.create_database(
            parent_page_id=parent_page_id,
            title=config.NOTION_DATABASE_TITLE,
            properties=_PROPRIEDADES_PADRAO,
        )

        novo_database_id = database["id"]
        novo_data_source_id = self.client.extrair_data_source_id(database)

        config.set_env_variable("NOTION_DATABASE_ID", novo_database_id)
        config.set_env_variable("NOTION_DATA_SOURCE_ID", novo_data_source_id)
        config.reload()

        self.database_id = novo_database_id
        self.data_source_id = novo_data_source_id

        print(f"Database '{config.NOTION_DATABASE_TITLE}' criada. IDs salvos no .env.")

        return novo_data_source_id

    def _resolver_pagina_pai(self) -> str:
        """
        Resolve a página-pai necessária para criar a Database.

        A API do Notion não permite criar uma página raiz no workspace:
        uma integração só pode agir dentro de páginas já compartilhadas
        manualmente com ela ("Connect to" no menu "..." da página no
        Notion). Por isso:

        1. Se NOTION_PARENT_PAGE_ID estiver definido no .env, usa ela.
        2. Caso contrário, busca a primeira página compartilhada com a
           integração e usa essa.
        3. Se nenhuma página compartilhada for encontrada, não há como
           prosseguir — é uma restrição oficial da API, não um bug.
        """

        if config.NOTION_PARENT_PAGE_ID:
            return config.NOTION_PARENT_PAGE_ID

        paginas = self.client.search_pages()

        if paginas:
            pagina = paginas[0]
            print(
                "Nenhum NOTION_PARENT_PAGE_ID definido no .env. "
                f"Usando automaticamente a página compartilhada '{pagina['id']}' "
                "como página-pai."
            )
            return pagina["id"]

        raise RuntimeError(
            "Não foi possível criar a Database: nenhuma página do Notion está "
            "compartilhada com esta integração, e a API do Notion não permite "
            "criar páginas raiz no workspace automaticamente.\n\n"
            "Solução: abra o Notion, crie (ou escolha) uma página, clique em "
            "'...' > 'Connect to' e selecione sua integração. Opcionalmente, "
            "copie o ID dessa página e adicione ao .env como "
            "NOTION_PARENT_PAGE_ID=<id-da-pagina>."
        )

    # =====================================================
    # MAPEAMENTO DE PROPRIEDADES
    # =====================================================

    def _titulo(self, valor: Optional[str]) -> Dict[str, Any]:
        return {"title": [{"text": {"content": valor or ""}}]}

    def _texto(self, valor: Optional[str]) -> Dict[str, Any]:
        return {"rich_text": [{"text": {"content": valor or ""}}]}

    def _telefone(self, valor: Optional[str]) -> Dict[str, Any]:
        return {"phone_number": valor or None}

    def _select(self, valor: Optional[str]) -> Dict[str, Any]:
        if not valor:
            return {"select": None}
        return {"select": {"name": str(valor)}}

    def _data(self, valor: Optional[Any]) -> Dict[str, Any]:
        if not valor:
            return {"date": None}
        if isinstance(valor, (datetime, date)):
            return {"date": {"start": valor.isoformat()}}
        return {"date": {"start": str(valor)}}

    def _propriedades_do_registro(self, record: ProspeccaoRecord) -> Dict[str, Any]:

        return {
            "Nome": self._titulo(record.nome),
            "CPF": self._texto(record.cpf),
            "Telefone": self._telefone(record.telefone_assertivo),
            "Cidade": self._texto(record.cidade),
            "UF": self._select(record.uf),
            "Categoria": self._select(record.categoria),
            "Posto": self._select(record.posto),
            "Origem": self._select(record.origem),
            "Status": self._select(record.status),
            "Observações": self._texto(record.observacoes),
            "Data Cadastro": self._data(record.data_cadastro),
            "Primeiro Contato": self._data(record.data_primeiro_contato),
            "Última Atualização": self._data(record.ultima_atualizacao),
            "Matrícula": self._texto(record.matricula),
        }

    # =====================================================
    # LEITURA DE PROPRIEDADES (NOTION -> POSTGRES)
    # =====================================================

    def _ler_titulo(self, prop: Dict[str, Any]) -> Optional[str]:
        itens = (prop or {}).get("title", [])
        texto = "".join(item.get("plain_text", "") for item in itens)
        return texto or None

    def _ler_texto(self, prop: Dict[str, Any]) -> Optional[str]:
        itens = (prop or {}).get("rich_text", [])
        texto = "".join(item.get("plain_text", "") for item in itens)
        return texto or None

    def _ler_select(self, prop: Dict[str, Any]) -> Optional[str]:
        valor = (prop or {}).get("select")
        return valor["name"] if valor else None

    def _ler_telefone(self, prop: Dict[str, Any]) -> Optional[str]:
        return (prop or {}).get("phone_number")

    def _ler_data(self, prop: Dict[str, Any]) -> Optional[str]:
        valor = (prop or {}).get("date")
        return valor["start"] if valor else None

    def _campos_editaveis_da_pagina(self, pagina: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """
        Extrai da página do Notion apenas os campos que fazem sentido
        serem editados manualmente por quem usa o painel (status,
        observações, telefone, cidade, etc.). Campos "de sistema" como
        Nome, CPF, Origem e Data Cadastro não voltam para o Postgres.
        """

        props = pagina.get("properties", {})

        return {
            "status": self._ler_select(props.get("Status")),
            "observacoes": self._ler_texto(props.get("Observações")),
            "telefone_assertivo": self._ler_telefone(props.get("Telefone")),
            "cidade": self._ler_texto(props.get("Cidade")),
            "uf": self._ler_select(props.get("UF")),
            "categoria": self._ler_select(props.get("Categoria")),
            "posto": self._ler_select(props.get("Posto")),
            "matricula": self._ler_texto(props.get("Matrícula")),
            "data_primeiro_contato": self._ler_data(props.get("Primeiro Contato")),
        }

    # =====================================================
    # IMPORTAÇÃO (NOTION -> POSTGRES)
    # =====================================================

    def importar_do_notion(self, repositorio: Any) -> Dict[str, int]:
        """
        Lê todas as páginas da Database no Notion e replica os campos
        editáveis (status, observações, etc.) de volta para o Postgres,
        usando o CPF como chave. Isso permite que alguém mude o Status
        de um lead direto no painel do Notion e essa mudança "grude"
        no banco oficial.

        Deve ser chamado ANTES do sync_prospeccao() (Postgres -> Notion)
        na mesma execução, para que a edição feita no Notion seja
        absorvida pelo Postgres e, na sequência, reafirmada de volta no
        Notion — evitando que o passo seguinte sobrescreva a edição com
        um valor antigo.
        """

        if not self.data_source_id:
            raise RuntimeError("ensure_database() precisa ser chamado antes do importar_do_notion().")

        resumo = {"processados": 0, "atualizados": 0, "ignorados": 0}

        paginas = self.client.query_data_source_all(self.data_source_id)

        for pagina in paginas:

            resumo["processados"] += 1

            props = pagina.get("properties", {})
            cpf = self._ler_texto(props.get("CPF"))

            if not cpf:
                resumo["ignorados"] += 1
                continue

            campos = self._campos_editaveis_da_pagina(pagina)

            try:
                repositorio.atualizar_prospeccao(cpf=cpf, **campos)
                resumo["atualizados"] += 1
            except Exception as erro:
                print(f"Erro ao importar CPF {cpf} do Notion: {erro}")
                resumo["ignorados"] += 1

        return resumo

    # =====================================================
    # UPSERT (POSTGRES -> NOTION)
    # =====================================================

    def upsert(self, record: ProspeccaoRecord) -> SyncAction:
        """
        Cria ou atualiza a página do Notion correspondente ao CPF do
        registro. O CPF é sempre a chave única de busca — nunca cria
        duplicatas.
        """

        if not self.data_source_id:
            raise RuntimeError("ensure_database() precisa ser chamado antes do upsert().")

        if not record.cpf:
            return SyncAction.IGNORADO

        propriedades = self._propriedades_do_registro(record)

        pagina_existente = self.client.find_page_by_cpf(self.data_source_id, record.cpf)

        if pagina_existente:
            self.client.update_page(pagina_existente["id"], propriedades)
            return SyncAction.ATUALIZADO

        self.client.create_page(self.data_source_id, propriedades)
        return SyncAction.CRIADO