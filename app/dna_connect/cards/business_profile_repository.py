from app.dna_connect.database.connection import Database
from app.dna_connect.cards.models import CardBusinessProfile


# profile_photo fica FORA desta lista de propósito: é gerenciado pelos
# métodos dedicados de foto (salvar_foto/remover_foto), nunca pelo
# upsert genérico de texto — assim, salvar os demais campos do perfil
# (Sprint 26) nunca sobrescreve/apaga a foto enviada (Sprint 28).
#
# instagram/linkedin/facebook/tiktok/youtube também ficam FORA de
# propósito (Sprint 4 do roadmap Airgo): essas colunas ainda existem
# no banco (nunca foram apagadas, sem risco de perda de dado), mas
# desde a lista livre de links (tabela card_links) o app não lê nem
# escreve mais nelas — se estivessem aqui, o upsert genérico as
# sobrescreveria com NULL no primeiro salvamento após essa mudança,
# apagando dados de cartões antigos que nunca chegaram a ser migrados
# manualmente. Ver CardLinksRepository.migrar_redes_legadas.
CAMPOS_PERFIL = [
    "name",
    "professional_title",
    "company",
    "whatsapp",
    "phone",
    "email",
    "website",
    "pix_key",
    "pix_key_type",
    "pix_beneficiary_name",
    "pix_beneficiary_city",
    "bio",
    "background_color",
    "google_maps_url",
    "accent_color",
    "background_type",
    "gradient_color_1",
    "gradient_color_2",
    "gradient_direction"
]


class CardBusinessProfileRepository:

    def __init__(self):

        self.db = Database()

    # =====================================================
    # ESTRUTURA
    # =====================================================

    def criar_tabela(self):

        cursor = self.db.cursor()

        cursor.execute("""

            CREATE TABLE IF NOT EXISTS card_business_profiles (

                id SERIAL PRIMARY KEY,
                card_id INTEGER NOT NULL UNIQUE REFERENCES cards (id),

                name TEXT,
                professional_title TEXT,
                company TEXT,
                profile_photo TEXT,

                whatsapp TEXT,
                phone TEXT,
                email TEXT,

                instagram TEXT,
                linkedin TEXT,
                facebook TEXT,
                tiktok TEXT,
                youtube TEXT,
                website TEXT,

                pix_key TEXT,
                pix_key_type TEXT,

                bio TEXT,

                background_color TEXT,

                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()

            )

        """)

        self.db.commit()

    def adicionar_colunas_foto_upload(self):
        """
        Colunas para a foto enviada via upload (Sprint 28): os bytes da
        imagem e o content-type real detectado no backend. Persistidas
        no próprio Postgres — já é a infraestrutura de armazenamento
        persistente do projeto, sobrevive a redeploys/restarts do
        Render sem exigir nenhum serviço/credencial nova.
        """

        cursor = self.db.cursor()

        cursor.execute("""

            ALTER TABLE card_business_profiles
            ADD COLUMN IF NOT EXISTS profile_photo_data BYTEA

        """)

        cursor.execute("""

            ALTER TABLE card_business_profiles
            ADD COLUMN IF NOT EXISTS profile_photo_content_type VARCHAR(50)

        """)

        self.db.commit()

    def adicionar_colunas_personalizacao(self):
        """
        Colunas de personalização adicionadas na Sprint 31: link do
        Google Maps e cor de destaque (accent_color) dos botões/
        elementos do cartão de visita. Opcionais/NULL — cartões
        antigos continuam funcionando exatamente como antes (fallback
        para o azul padrão no accent_color, botão de mapa ausente).
        """

        cursor = self.db.cursor()

        cursor.execute("""

            ALTER TABLE card_business_profiles
            ADD COLUMN IF NOT EXISTS google_maps_url TEXT

        """)

        cursor.execute("""

            ALTER TABLE card_business_profiles
            ADD COLUMN IF NOT EXISTS accent_color TEXT

        """)

        self.db.commit()

    def adicionar_colunas_fundo_avancado(self):
        """
        Evolui a personalização do fundo do cartão de visita de uma
        única cor sólida para 3 modos (solid/gradient/image).

        background_type é opcional (sem NOT NULL) de propósito: cartões
        já existentes só têm background_color preenchido, então essa
        coluna nasce NULL para eles — o próprio código de leitura (ver
        card_business_profile, em cards/routes.py) trata NULL como
        'solid', preservando exatamente o comportamento atual sem
        precisar migrar nenhum dado. As colunas de imagem de fundo
        seguem o mesmo padrão já usado para profile_photo (Sprint 28):
        bytes salvos direto no Postgres, sem storage externo.
        """

        cursor = self.db.cursor()

        cursor.execute("""

            ALTER TABLE card_business_profiles
            ADD COLUMN IF NOT EXISTS background_type VARCHAR(20)

        """)

        cursor.execute("""

            DO $$
            BEGIN

                ALTER TABLE card_business_profiles
                ADD CONSTRAINT chk_card_business_profiles_background_type
                CHECK (background_type IS NULL OR background_type IN ('solid', 'gradient', 'image'));

            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;

        """)

        cursor.execute("""

            ALTER TABLE card_business_profiles
            ADD COLUMN IF NOT EXISTS gradient_color_1 TEXT

        """)

        cursor.execute("""

            ALTER TABLE card_business_profiles
            ADD COLUMN IF NOT EXISTS gradient_color_2 TEXT

        """)

        cursor.execute("""

            ALTER TABLE card_business_profiles
            ADD COLUMN IF NOT EXISTS gradient_direction VARCHAR(20)

        """)

        cursor.execute("""

            ALTER TABLE card_business_profiles
            ADD COLUMN IF NOT EXISTS background_image TEXT

        """)

        cursor.execute("""

            ALTER TABLE card_business_profiles
            ADD COLUMN IF NOT EXISTS background_image_data BYTEA

        """)

        cursor.execute("""

            ALTER TABLE card_business_profiles
            ADD COLUMN IF NOT EXISTS background_image_content_type VARCHAR(50)

        """)

        self.db.commit()

    def adicionar_colunas_pix_cobranca(self):
        """
        Sprint 5 do roadmap Airgo: nome e cidade do beneficiário,
        exigidos pelo padrão oficial do Banco Central para montar um
        QR Code de cobrança Pix válido (BR Code) — sem eles não dá pra
        gerar o payload, só continuar mostrando a chave (que já
        funcionava antes e continua funcionando sem essas colunas
        preenchidas, exatamente como hoje).
        """

        cursor = self.db.cursor()

        cursor.execute("""

            ALTER TABLE card_business_profiles
            ADD COLUMN IF NOT EXISTS pix_beneficiary_name TEXT

        """)

        cursor.execute("""

            ALTER TABLE card_business_profiles
            ADD COLUMN IF NOT EXISTS pix_beneficiary_city TEXT

        """)

        self.db.commit()

    # =====================================================
    # PERFIL
    # =====================================================

    def buscar_por_card_id(self, card_id: int):

        cursor = self.db.cursor()

        cursor.execute(f"""

            SELECT

                id,
                card_id,
                profile_photo,
                background_image,
                {", ".join(CAMPOS_PERFIL)},
                created_at,
                updated_at

            FROM card_business_profiles

            WHERE card_id = %s

        """, (card_id,))

        linha = cursor.fetchone()

        if not linha:
            return None

        dados_campos = dict(zip(CAMPOS_PERFIL, linha[4:4 + len(CAMPOS_PERFIL)]))

        return CardBusinessProfile(
            id=linha[0],
            card_id=linha[1],
            profile_photo=linha[2],
            background_image=linha[3],
            created_at=linha[4 + len(CAMPOS_PERFIL)],
            updated_at=linha[5 + len(CAMPOS_PERFIL)],
            **dados_campos
        )

    def salvar(self, card_id: int, dados: dict):
        """
        Insere ou atualiza (upsert) os campos de texto do perfil de
        cartão de visita. Campos não informados em `dados` são
        gravados como NULL, já que todos são opcionais. Nunca toca na
        foto (profile_photo/profile_photo_data/profile_photo_content_type)
        — ver comentário de CAMPOS_PERFIL.
        """

        valores = [dados.get(campo) for campo in CAMPOS_PERFIL]

        colunas = ", ".join(CAMPOS_PERFIL)
        placeholders = ", ".join(["%s"] * len(CAMPOS_PERFIL))
        atualizacoes = ", ".join(f"{campo} = EXCLUDED.{campo}" for campo in CAMPOS_PERFIL)

        cursor = self.db.cursor()

        cursor.execute(f"""

            INSERT INTO card_business_profiles (card_id, {colunas})
            VALUES (%s, {placeholders})
            ON CONFLICT (card_id) DO UPDATE SET
                {atualizacoes},
                updated_at = NOW()

        """, (card_id, *valores))

        self.db.commit()

    def remover_por_card_id(self, card_id: int):
        """
        Apaga o perfil de cartão de visita associado a um cartão (usado
        quando o cartão é desvinculado do dono, para que um futuro
        proprietário nunca herde dados de quem usou o cartão antes).
        A foto (colunas abaixo) é apagada junto, por estar na mesma
        linha/tabela.
        """

        cursor = self.db.cursor()

        cursor.execute("DELETE FROM card_business_profiles WHERE card_id = %s", (card_id,))

        self.db.commit()

    # =====================================================
    # FOTO (upload)
    # =====================================================

    def salvar_foto(self, card_id: int, dados_binarios: bytes, content_type: str, url_publica: str):
        """
        Insere ou atualiza (upsert) a foto de perfil enviada por
        upload. Substitui integralmente a foto anterior (não há
        histórico de fotos — apenas uma foto ativa por cartão).
        """

        cursor = self.db.cursor()

        cursor.execute("""

            INSERT INTO card_business_profiles (
                card_id, profile_photo, profile_photo_data, profile_photo_content_type
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (card_id) DO UPDATE SET
                profile_photo = EXCLUDED.profile_photo,
                profile_photo_data = EXCLUDED.profile_photo_data,
                profile_photo_content_type = EXCLUDED.profile_photo_content_type,
                updated_at = NOW()

        """, (card_id, url_publica, dados_binarios, content_type))

        self.db.commit()

    def remover_foto(self, card_id: int):
        """
        Remove a foto de perfil (volta ao placeholder/inicial já usado
        na página pública). Não afeta os demais campos do perfil.
        """

        cursor = self.db.cursor()

        cursor.execute("""

            UPDATE card_business_profiles

            SET

                profile_photo = NULL,
                profile_photo_data = NULL,
                profile_photo_content_type = NULL,
                updated_at = NOW()

            WHERE card_id = %s

        """, (card_id,))

        self.db.commit()

    def buscar_foto_por_card_id(self, card_id: int):
        """
        Retorna os bytes e o content-type da foto ativa de um cartão,
        ou None caso não exista (usado pela rota pública que serve a
        imagem).
        """

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT profile_photo_data, profile_photo_content_type

            FROM card_business_profiles

            WHERE card_id = %s

        """, (card_id,))

        linha = cursor.fetchone()

        if not linha or linha[0] is None:
            return None

        return {"dados": bytes(linha[0]), "content_type": linha[1]}

    # =====================================================
    # IMAGEM DE FUNDO (background_type = image)
    # =====================================================

    def salvar_imagem_fundo(self, card_id: int, dados_binarios: bytes, content_type: str, url_publica: str):
        """
        Insere ou atualiza (upsert) a imagem de fundo do cartão de
        visita. Mesmo padrão de salvar_foto: substitui integralmente a
        imagem anterior, sem histórico.
        """

        cursor = self.db.cursor()

        cursor.execute("""

            INSERT INTO card_business_profiles (
                card_id, background_image, background_image_data, background_image_content_type
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (card_id) DO UPDATE SET
                background_image = EXCLUDED.background_image,
                background_image_data = EXCLUDED.background_image_data,
                background_image_content_type = EXCLUDED.background_image_content_type,
                updated_at = NOW()

        """, (card_id, url_publica, dados_binarios, content_type))

        self.db.commit()

    def remover_imagem_fundo(self, card_id: int):
        """
        Remove a imagem de fundo (o cartão volta a usar cor sólida ou
        gradiente, conforme o background_type salvo). Não afeta os
        demais campos do perfil.
        """

        cursor = self.db.cursor()

        cursor.execute("""

            UPDATE card_business_profiles

            SET

                background_image = NULL,
                background_image_data = NULL,
                background_image_content_type = NULL,
                updated_at = NOW()

            WHERE card_id = %s

        """, (card_id,))

        self.db.commit()

    def buscar_imagem_fundo_por_card_id(self, card_id: int):
        """
        Retorna os bytes e o content-type da imagem de fundo ativa,
        usado pela rota pública que serve a imagem.
        """

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT background_image_data, background_image_content_type

            FROM card_business_profiles

            WHERE card_id = %s

        """, (card_id,))

        linha = cursor.fetchone()

        if not linha or linha[0] is None:
            return None

        return {"dados": bytes(linha[0]), "content_type": linha[1]}

    def fechar(self):

        self.db.close()
