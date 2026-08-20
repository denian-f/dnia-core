from app.dna_connect.database.connection import Database


class CardCatalogRepository:

    def __init__(self):

        self.db = Database()

    # =====================================================
    # ESTRUTURA
    # =====================================================

    def criar_tabela(self):

        cursor = self.db.cursor()

        cursor.execute("""

            CREATE TABLE IF NOT EXISTS card_catalog_items (

                id SERIAL PRIMARY KEY,
                card_id INTEGER NOT NULL REFERENCES cards (id),
                title TEXT NOT NULL,
                description TEXT,
                price TEXT,
                action_label TEXT,
                action_url TEXT,
                image_data BYTEA,
                image_content_type VARCHAR(50),
                posicao INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()

            )

        """)

        self.db.commit()

    # =====================================================
    # ITENS
    # =====================================================

    def listar_por_card_id(self, card_id: int):
        """
        Lista os itens do catálogo, ordenados pela posição configurada
        pelo dono. `tem_imagem` indica se o item tem foto própria, sem
        trazer os bytes (que são servidos por rota dedicada, mesmo
        padrão já usado para foto de perfil/imagem de fundo).
        """

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT
                id, title, description, price, action_label, action_url,
                (image_data IS NOT NULL) AS tem_imagem, posicao

            FROM card_catalog_items

            WHERE card_id = %s

            ORDER BY posicao, id

        """, (card_id,))

        return [
            {
                "id": linha[0],
                "title": linha[1],
                "description": linha[2],
                "price": linha[3],
                "action_label": linha[4],
                "action_url": linha[5],
                "tem_imagem": linha[6],
                "posicao": linha[7]
            }
            for linha in cursor.fetchall()
        ]

    def buscar_ids_por_card_id(self, card_id: int):

        cursor = self.db.cursor()

        cursor.execute("SELECT id FROM card_catalog_items WHERE card_id = %s", (card_id,))

        return {linha[0] for linha in cursor.fetchall()}

    def criar_item(self, card_id: int, dados: dict, posicao: int, imagem_bytes=None, imagem_content_type=None):

        cursor = self.db.cursor()

        cursor.execute("""

            INSERT INTO card_catalog_items (
                card_id, title, description, price, action_label, action_url,
                image_data, image_content_type, posicao
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id

        """, (
            card_id, dados["title"], dados["description"], dados["price"],
            dados["action_label"], dados["action_url"],
            imagem_bytes, imagem_content_type, posicao
        ))

        novo_id = cursor.fetchone()[0]

        self.db.commit()

        return novo_id

    def atualizar_item(self, item_id: int, dados: dict, posicao: int, imagem_bytes=None, imagem_content_type=None):
        """
        Atualiza um item existente. A imagem só é sobrescrita quando
        `imagem_bytes` é informado — assim, salvar o restante do
        catálogo (título, preço etc.) nunca apaga a foto de um item que
        não teve um novo arquivo enviado naquele envio do formulário.
        """

        cursor = self.db.cursor()

        if imagem_bytes is not None:

            cursor.execute("""

                UPDATE card_catalog_items

                SET
                    title = %s, description = %s, price = %s,
                    action_label = %s, action_url = %s, posicao = %s,
                    image_data = %s, image_content_type = %s,
                    updated_at = NOW()

                WHERE id = %s

            """, (
                dados["title"], dados["description"], dados["price"],
                dados["action_label"], dados["action_url"], posicao,
                imagem_bytes, imagem_content_type, item_id
            ))

        else:

            cursor.execute("""

                UPDATE card_catalog_items

                SET
                    title = %s, description = %s, price = %s,
                    action_label = %s, action_url = %s, posicao = %s,
                    updated_at = NOW()

                WHERE id = %s

            """, (
                dados["title"], dados["description"], dados["price"],
                dados["action_label"], dados["action_url"], posicao,
                item_id
            ))

        self.db.commit()

    def remover_item(self, item_id: int):

        cursor = self.db.cursor()

        cursor.execute("DELETE FROM card_catalog_items WHERE id = %s", (item_id,))

        self.db.commit()

    def buscar_imagem_por_item_id(self, item_id: int):

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT image_data, image_content_type

            FROM card_catalog_items

            WHERE id = %s

        """, (item_id,))

        linha = cursor.fetchone()

        if not linha or linha[0] is None:
            return None

        return {"dados": bytes(linha[0]), "content_type": linha[1]}

    def fechar(self):

        self.db.close()
