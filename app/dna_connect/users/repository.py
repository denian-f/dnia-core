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

    def adicionar_colunas_verificacao_email(self):

        cursor = self.db.cursor()

        # DEFAULT TRUE na criação da coluna faz com que contas já
        # existentes (cadastradas antes desta sprint) sejam consideradas
        # verificadas automaticamente. Em seguida o DEFAULT é trocado
        # para FALSE, valendo apenas para cadastros novos a partir daqui.
        cursor.execute("""

            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT TRUE

        """)

        cursor.execute("""

            ALTER TABLE users
            ALTER COLUMN email_verified SET DEFAULT FALSE

        """)

        cursor.execute("""

            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS email_verification_token_hash VARCHAR(64)

        """)

        cursor.execute("""

            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS email_verification_expires_at TIMESTAMP

        """)

        cursor.execute("""

            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS email_verification_last_sent_at TIMESTAMP

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
                email_verified,
                email_verification_token_hash,
                email_verification_expires_at,
                email_verification_last_sent_at,
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
            email_verified=linha[5],
            email_verification_token_hash=linha[6],
            email_verification_expires_at=linha[7],
            email_verification_last_sent_at=linha[8],
            created_at=linha[9],
            updated_at=linha[10]
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
                email_verified,
                email_verification_token_hash,
                email_verification_expires_at,
                email_verification_last_sent_at,
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
            email_verified=linha[5],
            email_verification_token_hash=linha[6],
            email_verification_expires_at=linha[7],
            email_verification_last_sent_at=linha[8],
            created_at=linha[9],
            updated_at=linha[10]
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

            RETURNING
                id, name, email, password_hash, is_admin,
                email_verified, email_verification_token_hash,
                email_verification_expires_at, email_verification_last_sent_at,
                created_at, updated_at

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
            email_verified=linha[5],
            email_verification_token_hash=linha[6],
            email_verification_expires_at=linha[7],
            email_verification_last_sent_at=linha[8],
            created_at=linha[9],
            updated_at=linha[10]
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

            RETURNING
                id, name, email, password_hash, is_admin,
                email_verified, email_verification_token_hash,
                email_verification_expires_at, email_verification_last_sent_at,
                created_at, updated_at

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
            email_verified=linha[5],
            email_verification_token_hash=linha[6],
            email_verification_expires_at=linha[7],
            email_verification_last_sent_at=linha[8],
            created_at=linha[9],
            updated_at=linha[10]
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

    def definir_token_verificacao(self, user_id: int, token_hash: str, expires_at):

        cursor = self.db.cursor()

        cursor.execute("""

            UPDATE users

            SET

                email_verification_token_hash = %s,
                email_verification_expires_at = %s,
                email_verification_last_sent_at = NOW(),
                updated_at = NOW()

            WHERE id = %s

        """, (

            token_hash,
            expires_at,
            user_id

        ))

        self.db.commit()

    def buscar_por_token_hash(self, token_hash: str):

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT

                id,
                name,
                email,
                password_hash,
                is_admin,
                email_verified,
                email_verification_token_hash,
                email_verification_expires_at,
                email_verification_last_sent_at,
                created_at,
                updated_at

            FROM users

            WHERE email_verification_token_hash = %s

        """, (token_hash,))

        linha = cursor.fetchone()

        if not linha:
            return None

        return User(
            id=linha[0],
            name=linha[1],
            email=linha[2],
            password_hash=linha[3],
            is_admin=linha[4],
            email_verified=linha[5],
            email_verification_token_hash=linha[6],
            email_verification_expires_at=linha[7],
            email_verification_last_sent_at=linha[8],
            created_at=linha[9],
            updated_at=linha[10]
        )

    def marcar_email_verificado(self, user_id: int):

        cursor = self.db.cursor()

        cursor.execute("""

            UPDATE users

            SET

                email_verified = TRUE,
                email_verification_token_hash = NULL,
                email_verification_expires_at = NULL,
                updated_at = NOW()

            WHERE id = %s

        """, (user_id,))

        self.db.commit()

    def fechar(self):

        self.db.close()
