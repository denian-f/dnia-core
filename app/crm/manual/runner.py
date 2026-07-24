"""
Envia um Cliente já extraído (via parser.extrair_cliente) para o
mesmo fluxo de persistência do Collector: CRMExporter -> PostgresRepository.

Nenhuma regra de negócio de banco é duplicada aqui — CRMExporter e
PostgresRepository são reaproveitados sem alterações.
"""

from __future__ import annotations

from typing import Tuple

from app.crm.collector.excel.exporter import CRMExporter
from app.crm.collector.models.cliente import Cliente


class ManualRunner:

    def __init__(self) -> None:

        self.exporter = CRMExporter()

    def processar(self, cliente: Cliente) -> Tuple[Cliente, bool]:

        cliente_novo = self.exporter.adicionar_cliente(cliente)

        self.exporter.adicionar_contratos(cliente)

        self.exporter.salvar()

        return cliente, cliente_novo

    def finalizar(self) -> None:

        self.exporter.fechar()
