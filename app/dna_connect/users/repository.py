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

    def adicionar_coluna_is_admin(self):

        cursor = self.db.cursor()

        cursor.execute("""

            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE

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
                is_admin,
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
            is_admin=linha[4],
            created_at=linha[5],
            updated_at=linha[6]
        )

    def buscar_por_id(self, user_id: int):

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT

                id,
                name,
                email,
                password_hash,
                is_admin,
                created_at,
                updated_at

            FROM users

            WHERE id = %s

        """, (user_id,))

        linha = cursor.fetchone()

        if not linha:
            return None

        return User(
            id=linha[0],
            name=linha[1],
            email=linha[2],
            password_hash=linha[3],
            is_admin=linha[4],
            created_at=linha[5],
            updated_at=linha[6]
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

            RETURNING id, name, email, password_hash, is_admin, created_at, updated_at

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
            is_admin=linha[4],
            created_at=linha[5],
            updated_at=linha[6]
        )

    def atualizar_perfil(self, user_id: int, name: str, email: str):

        cursor = self.db.cursor()

        cursor.execute("""

            UPDATE users

            SET

                name = %s,
                email = %s,
                updated_at = NOW()

            WHERE id = %s

            RETURNING id, name, email, password_hash, is_admin, created_at, updated_at

        """, (

            name,
            email,
            user_id

        ))

        linha = cursor.fetchone()

        self.db.commit()

        return User(
            id=linha[0],
            name=linha[1],
            email=linha[2],
            password_hash=linha[3],
            is_admin=linha[4],
            created_at=linha[5],
            updated_at=linha[6]
        )

    def atualizar_senha(self, user_id: int, password_hash: str):

        cursor = self.db.cursor()

        cursor.execute("""

            UPDATE users

            SET

                password_hash = %s,
                updated_at = NOW()

            WHERE id = %s

        """, (

            password_hash,
            user_id

        ))

        self.db.commit()

    def promover_admin(self, user_id: int):

        cursor = self.db.cursor()

        cursor.execute("""

            UPDATE users

            SET

                is_admin = TRUE,
                updated_at = NOW()

            WHERE id = %s

        """, (user_id,))

        self.db.commit()

    def fechar(self):

        self.db.close()
