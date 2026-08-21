import os

from dotenv import load_dotenv

load_dotenv()


# Caminho local do banco MaxMind GeoLite2 (arquivo .mmdb) — nunca uma
# credencial, só um caminho de arquivo no disco do servidor. Sem essa
# variável configurada, a resolução de localização fica desligada
# (retorna sempre None) e o resto do Analytics funciona normalmente,
# só sem país/região/cidade.
GEOLITE2_DATABASE_PATH = os.getenv("GEOLITE2_DATABASE_PATH", "").strip() or None

# Janela de retenção do cookie de visitante (Sprint Analytics): quantos
# dias o mesmo navegador precisa retornar dentro desse prazo para
# continuar sendo contado como "o mesmo visitante" em vez de um novo.
VISITOR_COOKIE_DAYS = int(os.getenv("ANALYTICS_VISITOR_COOKIE_DAYS", "90"))

# Política de retenção proposta (não há exclusão automática ainda —
# ver limitações conhecidas no relatório final da sprint): eventos
# detalhados ficam guardados por esse período; dados agregados
# (cálculos feitos em cima deles) não são persistidos separadamente
# nesta versão, então essa constante hoje só documenta a política.
EVENTS_RETENTION_DAYS = int(os.getenv("ANALYTICS_EVENTS_RETENTION_DAYS", "90"))
