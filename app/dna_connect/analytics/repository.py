from psycopg.types.json import Jsonb

from app.dna_connect.database.connection import Database


class AnalyticsRepository:

    def __init__(self):

        self.db = Database()

    def criar_tabela(self):

        cursor = self.db.cursor()

        cursor.execute("""

            CREATE TABLE IF NOT EXISTS analytics_events (

                id BIGSERIAL PRIMARY KEY,
                card_id INTEGER NOT NULL REFERENCES cards (id),
                visitor_id UUID NOT NULL,
                event_type VARCHAR(30) NOT NULL,
                metadata JSONB,
                country VARCHAR(2),
                region VARCHAR(100),
                city VARCHAR(100),
                device_type VARCHAR(15),
                os_name VARCHAR(20),
                browser_name VARCHAR(20),
                referrer_source VARCHAR(20),
                created_at TIMESTAMP NOT NULL DEFAULT NOW()

            )

        """)

        cursor.execute("""

            CREATE INDEX IF NOT EXISTS idx_analytics_events_card_created
            ON analytics_events (card_id, created_at)

        """)

        cursor.execute("""

            CREATE INDEX IF NOT EXISTS idx_analytics_events_card_type
            ON analytics_events (card_id, event_type)

        """)

        cursor.execute("""

            CREATE INDEX IF NOT EXISTS idx_analytics_events_visitor
            ON analytics_events (visitor_id)

        """)

        self.db.commit()

    def registrar_evento(
        self,
        card_id: int,
        visitor_id: str,
        event_type: str,
        metadata=None,
        country=None,
        region=None,
        city=None,
        device_type=None,
        os_name=None,
        browser_name=None,
        referrer_source=None
    ):

        cursor = self.db.cursor()

        cursor.execute("""

            INSERT INTO analytics_events (
                card_id, visitor_id, event_type, metadata, country, region, city,
                device_type, os_name, browser_name, referrer_source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)

        """, (
            card_id, visitor_id, event_type, Jsonb(metadata) if metadata else None,
            country, region, city, device_type, os_name, browser_name, referrer_source
        ))

        self.db.commit()

    def listar_eventos(self, card_ids: list, desde):
        """
        Retorna as linhas cruas do período — a agregação (contagens,
        gráficos, comparação de período) é feita em Python, no service
        (ver obter_analytics). Não há volume de acesso esperado que
        justifique múltiplas queries de agregação em SQL nesta escala
        (cartão de visita, não um site de alto tráfego); se o volume
        crescer muito no futuro, essa é a camada a otimizar primeiro.
        """

        if not card_ids:
            return []

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT
                event_type, visitor_id, metadata, country, region, city,
                device_type, os_name, browser_name, referrer_source, created_at

            FROM analytics_events

            WHERE card_id = ANY(%s) AND created_at >= %s

            ORDER BY created_at

        """, (card_ids, desde))

        return cursor.fetchall()

    def fechar(self):

        self.db.close()
