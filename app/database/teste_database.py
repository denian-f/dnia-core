from app.database.repository import PostgresRepository

repo = PostgresRepository()

pendentes = repo.clientes_pendentes()

linha = pendentes[0]["linha"]

repo.salvar_validacao(
    linha,
    "84"
)

print("Atualizado!")

repo.fechar()