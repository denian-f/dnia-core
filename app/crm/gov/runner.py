from app.crm.gov.services.gerar_validacao import gerar_validacao
from app.crm.gov.services.validacao import executar_validacao


class GovRunner:

    def executar(self):

        gerar_validacao()

        executar_validacao()