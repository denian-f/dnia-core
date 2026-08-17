import psycopg

from app.dna_connect.admin import config
from app.dna_connect.cards.repository import CardRepository
from app.dna_connect.cards.service import gerar_codigo_cartao
from app.dna_connect.users.service import promover_usuario_admin


_MAX_TENTATIVAS_GERACAO_CODIGO = 10


def bootstrap_admin():
    """
    Concede permissão administrativa ao usuário definido em
    DNA_CONNECT_ADMIN_EMAIL, caso a variável esteja configurada e o
    usuário já exista. Nunca cria um usuário novo. Idempotente.
    """

    email = config.DNA_CONNECT_ADMIN_EMAIL

    if not email:
        return

    promover_usuario_admin(email)


def listar_todos_cartoes_admin():
    """
    Retorna todos os cartões do sistema (visão administrativa) com um
    resumo agregado. Reaproveita o CardRepository existente.
    """

    repo = CardRepository()

    try:

        cartoes = repo.listar_todos_admin()

    finally:

        repo.fechar()

    total = len(cartoes)
    ativados = sum(1 for cartao in cartoes if cartao["activated"])

    return {
        "cartoes": cartoes,
        "resumo": {
            "total": total,
            "activated": ativados,
            "available": total - ativados
        }
    }


def criar_cartao_admin(card_code: str):
    """
    Cadastra um novo cartão físico, disponível para futura ativação
    (owner_id/target_url nulos, activated=False). A normalização
    (strip + uppercase) é aplicada apenas a cartões cadastrados a
    partir desta função, sem afetar códigos já existentes no banco.
    """

    if not card_code or not card_code.strip():
        return {"status": "code_required"}

    codigo_normalizado = card_code.strip().upper()

    repo = CardRepository()

    try:

        existente = repo.buscar_por_codigo(codigo_normalizado)

        if existente:
            return {"status": "code_exists"}

        repo.criar_cartao_disponivel(code=codigo_normalizado)

    finally:

        repo.fechar()

    return {"status": "created", "card_code": codigo_normalizado}


def gerar_cartao_automatico_admin():
    """
    Cadastra um novo cartão físico com código gerado automaticamente
    (Criação rápida), reutilizando exatamente o mesmo INSERT do
    cadastro manual (CardRepository.criar_cartao_disponivel) — o único
    cartão resultante é o cartão padrão do sistema, disponível para
    ativação (owner_id/target_url nulos, activated=False).

    A checagem prévia via buscar_por_codigo cobre o caso comum de
    colisão; como `code` é UNIQUE NOT NULL no banco, o retry ao
    capturar UniqueViolation cobre a corrida entre a verificação e o
    INSERT (duas gerações simultâneas sorteando o mesmo código), sem
    depender apenas de "gerar -> consultar -> inserir".
    """

    repo = CardRepository()

    try:

        for _ in range(_MAX_TENTATIVAS_GERACAO_CODIGO):

            codigo = gerar_codigo_cartao()

            if repo.buscar_por_codigo(codigo):
                continue

            try:

                repo.criar_cartao_disponivel(code=codigo)

            except psycopg.errors.UniqueViolation:

                repo.db.rollback()
                continue

            return {"status": "created", "card_code": codigo}

    finally:

        repo.fechar()

    return {"status": "generation_failed"}
