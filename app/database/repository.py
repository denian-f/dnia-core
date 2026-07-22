from datetime import datetime

from app.database.connection import Database


class PostgresRepository:

    def __init__(self):

        self.db = Database()

    # =====================================================
    # CLIENTES
    # =====================================================

    def listar_clientes(self):

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT

                nome,
                cpf,
                matricula,
                nascimento,
                idade,
                categoria,
                posto,
                cidade,
                uf,
                telefones,
                qtd_telefones

            FROM clientes

            ORDER BY nome

        """)

        return cursor.fetchall()

    # =====================================================
    # PROSPECÇÃO
    # =====================================================

    def listar_prospeccao(self):

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT

                cpf,
                nome,
                telefone_assertivo,
                cidade,
                uf,
                categoria,
                posto,
                origem,
                data_cadastro,
                status,
                data_primeiro_contato,
                ultima_atualizacao,
                observacoes,
                matricula

            FROM prospeccao

            ORDER BY nome

        """)

        return cursor.fetchall()

    def adicionar_prospeccao(self, cliente):

        cursor = self.db.cursor()

        agora = datetime.now()

        cursor.execute("""

            INSERT INTO prospeccao (

                cpf,
                nome,
                telefone_assertivo,
                cidade,
                uf,
                categoria,
                posto,
                origem,
                data_cadastro,
                status,
                data_primeiro_contato,
                ultima_atualizacao,
                observacoes,
                matricula

            )

            VALUES (

                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s

            )

        """, (

            cliente.cpf,
            cliente.nome,
            cliente.telefone,
            cliente.cidade,
            cliente.uf,
            cliente.categoria,
            cliente.posto,
            "CRM",
            agora,
            "NOVO",
            None,
            agora,
            "",
            getattr(cliente, "matricula", None)

        ))

        self.db.commit()

    # =====================================================
    # VALIDAÇÃO
    # =====================================================

    def listar_validacao(self):

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT

                cpf,
                nome,
                final_gov

            FROM validacao_gov

            ORDER BY nome

        """)

        return cursor.fetchall()

    def adicionar_validacao(
        self,
        cpf,
        nome
    ):

        cursor = self.db.cursor()

        cursor.execute("""

            INSERT INTO validacao_gov (

                cpf,
                nome,
                final_gov

            )

            VALUES (

                %s,
                %s,
                NULL

            )

        """, (

            cpf,
            nome

        ))

        self.db.commit()

    def clientes_pendentes(self):

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT

                cpf,
                nome,
                final_gov

            FROM validacao_gov

            WHERE final_gov IS NULL
               OR final_gov = ''

            ORDER BY nome

        """)

        clientes = []

        for indice, linha in enumerate(
            cursor.fetchall(),
            start=2
        ):

            clientes.append({

                "linha": indice,
                "cpf": linha[0],
                "nome": linha[1]

            })

        return clientes

    def salvar_validacao(
        self,
        linha,
        digitos
    ):

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT cpf

            FROM validacao_gov

            WHERE final_gov IS NULL
               OR final_gov = ''

            ORDER BY nome

        """)

        registros = cursor.fetchall()

        indice = linha - 2

        if indice < 0 or indice >= len(registros):
            return

        cpf = registros[indice][0]

        cursor.execute("""

            UPDATE validacao_gov

            SET final_gov = %s

            WHERE cpf = %s

        """, (

            digitos,
            cpf

        ))

        self.db.commit()

    # =====================================================
    # DATABASE
    # =====================================================

    def salvar(self):

        # Mantido apenas para compatibilidade
        # com os services existentes.

        self.db.commit()

    def fechar(self):

        self.db.close()