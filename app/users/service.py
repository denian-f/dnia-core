from app.users.repository import UserRepository


def init_users_db():
    """
    Garante a existência da tabela de usuários.
    """

    repo = UserRepository()

    try:

        repo.criar_tabela()

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
