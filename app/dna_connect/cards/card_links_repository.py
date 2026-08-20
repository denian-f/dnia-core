from app.dna_connect.database.connection import Database


_ICONES_VALIDOS = ("instagram", "linkedin", "facebook", "tiktok", "youtube", "link")

_REDES_LEGADAS = (
    ("instagram", "Instagram", "https://instagram.com/"),
    ("linkedin", "LinkedIn", "https://linkedin.com/in/"),
    ("facebook", "Facebook", "https://facebook.com/"),
    ("tiktok", "TikTok", "https://tiktok.com/@"),
    ("youtube", "YouTube", "https://youtube.com/")
)


class CardLinksRepository:

    def __init__(self):

        self.db = Database()

    # =====================================================
    # ESTRUTURA
    # =====================================================

    def criar_tabela(self):

        cursor = self.db.cursor()

        cursor.execute("""

            CREATE TABLE IF NOT EXISTS card_links (

                id SERIAL PRIMARY KEY,
                card_id INTEGER NOT NULL REFERENCES cards (id),
                label TEXT NOT NULL,
                url TEXT NOT NULL,
                icon VARCHAR(20) NOT NULL DEFAULT 'link',
                posicao INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()

            )

        """)

        self.db.commit()

    def migrar_redes_legadas(self):
        """
        Migração única e idempotente (Sprint 4): cartões que já tinham
        redes sociais preenchidas nos campos fixos antigos
        (instagram/linkedin/facebook/tiktok/youtube, de antes da
        criação da lista livre de links) e ainda não têm nenhuma linha
        em card_links recebem essas redes convertidas automaticamente
        — assim a página pública deles não perde os ícones no momento
        em que essa sprint entra no ar, sem exigir que o dono reabra o
        editor. As colunas antigas nunca são apagadas nem alteradas:
        essa migração só LÊ delas.

        O WHERE NOT EXISTS garante que isso nunca duplica dados, mesmo
        rodando a cada início da aplicação (mesmo padrão idempotente
        das demais migrações deste projeto).
        """

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT card_id, instagram, linkedin, facebook, tiktok, youtube

            FROM card_business_profiles

            WHERE (
                instagram IS NOT NULL OR linkedin IS NOT NULL OR facebook IS NOT NULL
                OR tiktok IS NOT NULL OR youtube IS NOT NULL
            )
            AND NOT EXISTS (
                SELECT 1 FROM card_links WHERE card_links.card_id = card_business_profiles.card_id
            )

        """)

        linhas = cursor.fetchall()

        for linha in linhas:

            card_id = linha[0]
            valores = linha[1:]
            posicao = 0

            for (icone, rotulo, url_base), valor in zip(_REDES_LEGADAS, valores):

                if not valor:
                    continue

                valor = valor.strip()
                url = valor if valor.startswith(("http://", "https://")) else f"{url_base}{valor.lstrip('@')}"

                cursor.execute("""

                    INSERT INTO card_links (card_id, label, url, icon, posicao)
                    VALUES (%s, %s, %s, %s, %s)

                """, (card_id, rotulo, url, icone, posicao))

                posicao += 1

        self.db.commit()

    # =====================================================
    # LINKS
    # =====================================================

    def listar_por_card_id(self, card_id: int):

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT id, label, url, icon, posicao

            FROM card_links

            WHERE card_id = %s

            ORDER BY posicao, id

        """, (card_id,))

        return [
            {"id": linha[0], "label": linha[1], "url": linha[2], "icon": linha[3], "posicao": linha[4]}
            for linha in cursor.fetchall()
        ]

    def substituir_links(self, card_id: int, links: list):
        """
        Substitui todos os links do cartão pela lista recebida, na
        ordem enviada (apaga tudo e reinsere) — mais simples e seguro
        do que tentar sincronizar add/remove/reordenar individualmente
        por ID a cada salvamento do formulário.
        """

        cursor = self.db.cursor()

        cursor.execute("DELETE FROM card_links WHERE card_id = %s", (card_id,))

        for posicao, link in enumerate(links):

            cursor.execute("""

                INSERT INTO card_links (card_id, label, url, icon, posicao)
                VALUES (%s, %s, %s, %s, %s)

            """, (card_id, link["label"], link["url"], link["icon"], posicao))

        self.db.commit()

    def fechar(self):

        self.db.close()
