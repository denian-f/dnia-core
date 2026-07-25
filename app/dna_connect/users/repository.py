from app.dna_connect.database.connection import Database
from app.dna_connect.users.models import User


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

    def adicionar_coluna_senha(self):

        cursor = self.db.cursor()

        cursor.execute("""

            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)

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
                password_hash,
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
            password_hash=linha[3],
            created_at=linha[4],
            updated_at=linha[5]
        )

    def criar_usuario(self, name: str, email: str, password_hash: str = None):

        cursor = self.db.cursor()

        cursor.execute("""

            INSERT INTO users (

                name,
                email,
                password_hash

            )

            VALUES (%s, %s, %s)

            RETURNING id, name, email, password_hash, created_at, updated_at

        """, (

            name,
            email,
            password_hash

        ))

        linha = cursor.fetchone()

        self.db.commit()

        return User(
            id=linha[0],
            name=linha[1],
            email=linha[2],
            password_hash=linha[3],
            created_at=linha[4],
            updated_at=linha[5]
        )

    def fechar(self):

        self.db.close()
