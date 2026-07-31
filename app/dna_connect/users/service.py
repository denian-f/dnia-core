import re

from app.dna_connect.users.repository import UserRepository
from app.security.hashing import hash_password, verify_password

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def init_users_db():
    """
    Garante a existência da tabela de usuários e da coluna de senha.
    """

    repo = UserRepository()

    try:

        repo.criar_tabela()
        repo.adicionar_coluna_senha()

    finally:

        repo.fechar()


def buscar_usuario_por_email(email: str):
    """
    Retorna o usuário com o e-mail informado, ou None caso não exista.
    """

    repo = UserRepository()

    try:

        return repo.buscar_por_email(email)

    finally:

        repo.fechar()


def registrar_usuario(name: str, email: str, password: str):
    """
    Cria uma conta permanente, com senha, para um novo usuário.
    """

    repo = UserRepository()

    try:

        existente = repo.buscar_por_email(email)

        if existente:
            return {"status": "email_exists"}

        password_hash = hash_password(password)

        user = repo.criar_usuario(
            name=name,
            email=email,
            password_hash=password_hash
        )

    finally:

        repo.fechar()

    return {"status": "created", "user": user}


def autenticar_usuario(email: str, password: str):
    """
    Valida e-mail e senha de um usuário.
    """

    user = buscar_usuario_por_email(email)

    if not user or not user.password_hash:
        return {"status": "invalid_credentials"}

    if not verify_password(password, user.password_hash):
        return {"status": "invalid_credentials"}

    return {"status": "authenticated", "user": user}


def listar_cartoes_do_usuario(email: str):
    """
    Retorna os cartões pertencentes ao usuário com o e-mail informado.
    """

    user = buscar_usuario_por_email(email)

    if not user:
        return {"status": "not_found"}

    # Import local para evitar importação circular
    from app.dna_connect.cards.service import listar_cartoes_por_owner

    cartoes = listar_cartoes_por_owner(user.id)

    return {"status": "ok", "cartoes": cartoes}


def _email_valido(email: str) -> bool:

    return bool(email) and bool(EMAIL_REGEX.match(email))


def atualizar_perfil_usuario(user_id: int, name: str, email: str):
    """
    Atualiza nome e e-mail do usuário autenticado.
    """

    if not name:
        return {"status": "name_required"}

    if not email:
        return {"status": "email_required"}

    if not _email_valido(email):
        return {"status": "invalid_email"}

    repo = UserRepository()

    try:

        existente = repo.buscar_por_email(email)

        if existente and existente.id != user_id:
            return {"status": "email_exists"}

        user = repo.atualizar_perfil(
            user_id=user_id,
            name=name,
            email=email
        )

    finally:

        repo.fechar()

    return {"status": "updated", "user": user}
