from dataclasses import dataclass


@dataclass
class Cliente:

    cpf: str
    nome: str

    telefone: str

    cidade: str
    uf: str

    categoria: str
    posto: str