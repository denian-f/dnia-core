from app.dna_connect.database.connection import Database
from app.dna_connect.cards.models import CardLead


class CardLeadsRepository:

    def __init__(self):

        self.db = Database()

    def criar_tabela(self):

        cursor = self.db.cursor()

        cursor.execute("""

            CREATE TABLE IF NOT EXISTS card_leads (

                id SERIAL PRIMARY KEY,
                card_id INTEGER NOT NULL REFERENCES cards (id),
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                message TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()

            )

        """)

        self.db.commit()

    def criar_lead(self, card_id: int, dados: dict):

        cursor = self.db.cursor()

        cursor.execute("""

            INSERT INTO card_leads (card_id, name, email, phone, message)
            VALUES (%s, %s, %s, %s, %s)

        """, (card_id, dados["name"], dados.get("email"), dados.get("phone"), dados.get("message")))

        self.db.commit()

    def listar_por_card_id(self, card_id: int):
        """
        Mais recentes primeiro — é assim que o dono do cartão vai
        querer ver quem entrou em contato.
        """

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT id, name, email, phone, message, created_at

            FROM card_leads

            WHERE card_id = %s

            ORDER BY created_at DESC

        """, (card_id,))

        return [
            CardLead(
                id=linha[0], card_id=card_id, name=linha[1], email=linha[2],
                phone=linha[3], message=linha[4], created_at=linha[5]
            )
            for linha in cursor.fetchall()
        ]

    def buscar_por_id(self, lead_id: int):

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT id, card_id, name, email, phone, message, created_at

            FROM card_leads

            WHERE id = %s

        """, (lead_id,))

        linha = cursor.fetchone()

        if not linha:
            return None

        return CardLead(
            id=linha[0], card_id=linha[1], name=linha[2], email=linha[3],
            phone=linha[4], message=linha[5], created_at=linha[6]
        )

    def remover(self, lead_id: int):

        cursor = self.db.cursor()

        cursor.execute("DELETE FROM card_leads WHERE id = %s", (lead_id,))

        self.db.commit()

    def fechar(self):

        self.db.close()
