from app.users.repository import UserRepository
from app.security.hashing import hash_password, verify_password


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
    from app.cards.service import listar_cartoes_por_owner

    cartoes = listar_cartoes_por_owner(user.id)

    return {"status": "ok", "cartoes": cartoes}
