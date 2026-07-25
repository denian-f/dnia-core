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


def buscar_ou_criar_usuario(name: str, email: str):
    """
    Retorna o usuário com o e-mail informado, criando-o caso não exista.
    """

    repo = UserRepository()

    try:

        user = repo.buscar_por_email(email)

        if user:
            return user

        return repo.criar_usuario(name=name, email=email)

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

    repo = UserRepository()

    try:

        user = repo.buscar_por_email(email)

    finally:

        repo.fechar()

    if not user or not user.password_hash:
        return {"status": "invalid_credentials"}

    if not verify_password(password, user.password_hash):
        return {"status": "invalid_credentials"}

    return {"status": "authenticated", "user": user}
