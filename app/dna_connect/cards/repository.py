from app.database.connection import Database
from app.cards.models import Card


class CardRepository:

    def __init__(self):

        self.db = Database()

    # =====================================================
    # ESTRUTURA
    # =====================================================

    def criar_tabela(self):

        cursor = self.db.cursor()

        cursor.execute("""

            CREATE TABLE IF NOT EXISTS cards (

                id SERIAL PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                target_url TEXT NOT NULL,
                activated BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()

            )

        """)

        self.db.commit()

    def criar_relacionamento_owner(self):

        cursor = self.db.cursor()

        cursor.execute("""

            ALTER TABLE cards
            ADD COLUMN IF NOT EXISTS owner_id INTEGER

        """)

        cursor.execute("""

            DO $$
            BEGIN

                ALTER TABLE cards
                ADD CONSTRAINT fk_cards_owner
                FOREIGN KEY (owner_id) REFERENCES users (id);

            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;

        """)

        self.db.commit()

    def seed_cartao_teste(self):

        cursor = self.db.cursor()

        cursor.execute("""

            INSERT INTO cards (

                code,
                target_url,
                activated

            )

            VALUES (%s, %s, %s)

            ON CONFLICT (code) DO NOTHING

        """, (

            "TESTE01",
            "https://github.com",
            True

        ))

        self.db.commit()

    # =====================================================
    # CARTÕES
    # =====================================================

    def buscar_por_codigo(self, code: str):

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT

                id,
                code,
                target_url,
                activated,
                owner_id,
                created_at,
                updated_at

            FROM cards

            WHERE code = %s

        """, (code,))

        linha = cursor.fetchone()

        if not linha:
            return None

        return Card(
            id=linha[0],
            code=linha[1],
            target_url=linha[2],
            activated=linha[3],
            owner_id=linha[4],
            created_at=linha[5],
            updated_at=linha[6]
        )

    def listar_por_owner(self, owner_id: int):

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT

                id,
                code,
                target_url,
                activated,
                owner_id,
                created_at,
                updated_at

            FROM cards

            WHERE owner_id = %s

            ORDER BY code

        """, (owner_id,))

        return [
            Card(
                id=linha[0],
                code=linha[1],
                target_url=linha[2],
                activated=linha[3],
                owner_id=linha[4],
                created_at=linha[5],
                updated_at=linha[6]
            )
            for linha in cursor.fetchall()
        ]

    def vincular_usuario(self, code: str, owner_id: int):

        cursor = self.db.cursor()

        cursor.execute("""

            UPDATE cards

            SET

                owner_id = %s,
                activated = TRUE,
                updated_at = NOW()

            WHERE code = %s

        """, (

            owner_id,
            code

        ))

        self.db.commit()

    def fechar(self):

        self.db.close()
