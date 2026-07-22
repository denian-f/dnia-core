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

    def cliente_existe(self, cpf):

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT 1

            FROM clientes

            WHERE cpf = %s

        """, (cpf,))

        return cursor.fetchone() is not None
    
    def adicionar_cliente(self, cliente):

        if self.cliente_existe(cliente.cpf):

            print(f"{cliente.nome} já existe.")

            return False

        cursor = self.db.cursor()

        cursor.execute("""

            INSERT INTO clientes (

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

            )

            VALUES (

                %s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s

            )

        """, (

            cliente.nome,
            cliente.cpf,
            cliente.matricula,
            cliente.nascimento,
            cliente.idade,
            cliente.categoria,
            cliente.posto,
            cliente.cidade,
            cliente.uf,
            "; ".join(cliente.telefones),
            len(cliente.telefones)

        ))

        self.db.commit()

        print(f"{cliente.nome} salvo.")

        return True
    
    def contrato_existe(
        self,
        cpf,
        contrato
    ):

        cursor = self.db.cursor()

        cursor.execute("""

            SELECT 1

            FROM contratos

            WHERE cpf = %s
            AND contrato = %s

        """, (

            cpf,
            contrato

        ))

        return cursor.fetchone() is not None

    def _numero(self, valor):

        if valor is None:
            return None

        valor = str(valor).strip()

        if valor == "":
            return None

        valor = (
            valor
            .replace("R$", "")
            .replace("%", "")
            .replace("\xa0", "")
            .strip()
        )

        valor = valor.replace(".", "")
        valor = valor.replace(",", ".")

        return float(valor)

    def adicionar_contratos(
        self,
        cliente
    ):

        cursor = self.db.cursor()

        try:

            for contrato in cliente.contratos:

                if self.contrato_existe(
                    cliente.cpf,
                    contrato.contrato
                ):
                    continue
            

                cursor.execute("""

                    INSERT INTO contratos (

                        cpf,
                        banco,
                        contrato,
                        parcela,
                        prazo,
                        taxa,
                        quitacao,
                        valor_liberado

                    )

                    VALUES (

                        %s,%s,%s,%s,
                        %s,%s,%s,%s

                    )

                """, (

                    cliente.cpf,
                    contrato.banco,
                    contrato.contrato,
                    self._numero(contrato.parcela),

                    int(contrato.prazo) if contrato.prazo else None,

                    self._numero(contrato.taxa),

                    self._numero(contrato.quitacao),

                    self._numero(contrato.valor_liberado),

                ))

            self.db.commit()

        except Exception:
            
            self.db.rollback()
        
            raise

    # =====================================================
    # DATABASE
    # =====================================================

    def salvar(self):

        # Mantido apenas para compatibilidade
        # com os services existentes.

        self.db.commit()

    def fechar(self):

        self.db.close()