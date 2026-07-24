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
            created_at=linha[4],
            updated_at=linha[5]
        )

    def fechar(self):

        self.db.close()
