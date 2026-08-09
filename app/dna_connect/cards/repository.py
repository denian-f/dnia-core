from app.dna_connect.database.connection import Database
from app.dna_connect.cards.models import Card


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

    def permitir_target_url_nulo(self):

        cursor = self.db.cursor()

        cursor.execute("""

            ALTER TABLE cards
            ALTER COLUMN target_url DROP NOT NULL

        """)

        self.db.commit()

    def adicionar_coluna_mode(self):

        cursor = self.db.cursor()

        cursor.execute("""

            ALTER TABLE cards
            ADD COLUMN IF NOT EXISTS mode VARCHAR(20) NOT NULL DEFAULT 'custom_link'

        """)

        cursor.execute("""

            DO $$
            BEGIN

                ALTER TABLE cards
                ADD CONSTRAINT chk_cards_mode
                CHECK (mode IN ('custom_link', 'business_card'));

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
                mode,
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
            mode=linha[4],
            owner_id=linha[5],
            created_at=linha[6],
            updated_at=linha[7]
        )

    def listar_por_owner(self, owner_id: int):

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT

                id,
                code,
                target_url,
                activated,
                mode,
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
                mode=linha[4],
                owner_id=linha[5],
                created_at=linha[6],
                updated_at=linha[7]
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

    def atualizar_target_url(self, code: str, target_url: str):

        cursor = self.db.cursor()

        cursor.execute("""

            UPDATE cards

            SET

                target_url = %s,
                updated_at = NOW()

            WHERE code = %s

        """, (

            target_url,
            code

        ))

        self.db.commit()

    def atualizar_modo(self, code: str, mode: str):

        cursor = self.db.cursor()

        cursor.execute("""

            UPDATE cards

            SET

                mode = %s,
                updated_at = NOW()

            WHERE code = %s

        """, (

            mode,
            code

        ))

        self.db.commit()

    def remover_associacao(self, code: str):
        """
        Remoção lógica: desvincula o cartão do dono atual e devolve o
        modo para custom_link (o cartão pode ser reativado por outro
        proprietário futuramente, e não deve herdar mode/target_url de
        quem o usou antes).
        """

        cursor = self.db.cursor()

        cursor.execute("""

            UPDATE cards

            SET

                owner_id = NULL,
                activated = FALSE,
                target_url = NULL,
                mode = 'custom_link',
                updated_at = NOW()

            WHERE code = %s

        """, (code,))

        self.db.commit()

    def criar_cartao_disponivel(self, code: str):

        cursor = self.db.cursor()

        cursor.execute("""

            INSERT INTO cards (

                code,
                target_url,
                activated

            )

            VALUES (%s, NULL, FALSE)

        """, (code,))

        self.db.commit()

    def listar_todos_admin(self):

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT

                cards.code,
                cards.activated,
                cards.target_url,
                users.name,
                users.email,
                cards.created_at,
                cards.updated_at

            FROM cards

            LEFT JOIN users ON users.id = cards.owner_id

            ORDER BY cards.code

        """)

        return [
            {
                "code": linha[0],
                "activated": linha[1],
                "target_url": linha[2],
                "owner_name": linha[3],
                "owner_email": linha[4],
                "created_at": linha[5],
                "updated_at": linha[6]
            }
            for linha in cursor.fetchall()
        ]

    def fechar(self):

        self.db.close()
