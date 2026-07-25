from app.database.connection import Database
from app.users.models import User


class UserRepository:

    def __init__(self):

        self.db = Database()

    # =====================================================
    # ESTRUTURA
    # =====================================================

    def criar_tabela(self):

        cursor = self.db.cursor()

        cursor.execute("""

            CREATE TABLE IF NOT EXISTS users (

                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()

            )

        """)

        self.db.commit()

    # =====================================================
    # USUÁRIOS
    # =====================================================

    def buscar_por_email(self, email: str):

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT

                id,
                name,
                email,
                created_at,
                updated_at

            FROM users

            WHERE email = %s

        """, (email,))

        linha = cursor.fetchone()

        if not linha:
            return None

        return User(
            id=linha[0],
            name=linha[1],
            email=linha[2],
            created_at=linha[3],
            updated_at=linha[4]
        )

    def criar_usuario(self, name: str, email: str):

        cursor = self.db.cursor()

        cursor.execute("""

            INSERT INTO users (

                name,
                email

            )

            VALUES (%s, %s)

            RETURNING id, name, email, created_at, updated_at

        """, (

            name,
            email

        ))

        linha = cursor.fetchone()

        self.db.commit()

        return User(
            id=linha[0],
            name=linha[1],
            email=linha[2],
            created_at=linha[3],
            updated_at=linha[4]
        )

    def fechar(self):

        self.db.close()
