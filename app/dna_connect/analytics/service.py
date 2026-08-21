import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from app.dna_connect.analytics.repository import AnalyticsRepository
from app.dna_connect.analytics import geoip, device_parser
from app.dna_connect.analytics.br_states import montar_mapa_estados, GRID_COLS, GRID_ROWS
from app.dna_connect.cards.repository import CardRepository
from app.dna_connect.cards.service import listar_cartoes_por_owner


# Lista fechada de eventos válidos (Sprint Analytics) — resultado da
# auditoria de tudo que é clicável/enviável no cartão de visita
# público hoje: contatos fixos (WhatsApp/telefone/e-mail/Maps/site),
# a lista livre de links/redes sociais (Sprint 4), o catálogo (Sprint
# 6), o Pix — chave e cobrança (Sprints 26 e 5), o download do vCard
# (Sprint 1) e o envio do formulário de leads (Sprint 7). QR Code
# offline e PDF são baixados pelo DONO do cartão no editor, não pelo
# visitante, então não fazem parte deste rastreamento.
EVENTOS_VALIDOS = (
    "page_view",
    "whatsapp_click",
    "phone_click",
    "email_click",
    "google_maps_click",
    "website_click",
    "social_link_click",
    "vcard_download",
    "catalog_item_click",
    "pix_key_copy",
    "pix_qr_generate",
    "pix_copia_cola_copy",
    "lead_form_submit"
)

_ROTULOS_EVENTO = {
    "whatsapp_click": "WhatsApp",
    "phone_click": "Telefone",
    "email_click": "E-mail",
    "google_maps_click": "Google Maps",
    "website_click": "Website",
    "social_link_click": "Redes sociais / links",
    "vcard_download": "Salvar contato",
    "catalog_item_click": "Catálogo",
    "pix_key_copy": "Pix (copiar chave)",
    "pix_qr_generate": "Pix (gerar QR)",
    "pix_copia_cola_copy": "Pix (copiar código)",
    "lead_form_submit": "Formulário de contato"
}

_FILTROS_PERIODO = {
    "hoje": 1,
    "7d": 7,
    "30d": 30,
    "90d": 90
}

_ROTULOS_ORIGEM = {
    "qr": "QR Code",
    "instagram": "Instagram",
    "whatsapp": "WhatsApp",
    "google": "Google",
    "facebook": "Facebook",
    "linkedin": "LinkedIn",
    "twitter": "X / Twitter",
    "tiktok": "TikTok",
    "direct": "Direto / desconhecido",
    "unknown": "Direto / desconhecido"
}

_NOME_FILTRO_PERIODO = {
    "hoje": "Hoje",
    "7d": "Últimos 7 dias",
    "30d": "Últimos 30 dias",
    "90d": "Últimos 90 dias"
}


def _agora_utc():
    """
    Horário atual em UTC sem tzinfo, para comparar diretamente com os
    valores (naive) que o psycopg devolve para colunas TIMESTAMP — o
    mesmo padrão já usado em users/service.py.
    """

    return datetime.now(timezone.utc).replace(tzinfo=None)


def init_analytics_db():

    repo = AnalyticsRepository()

    try:

        repo.criar_tabela()

    finally:

        repo.fechar()


def gerar_visitor_id() -> str:
    """
    UUID aleatório — não é derivado do IP, não usa fingerprinting, não
    contém nenhum dado pessoal. Serve só para o mesmo navegador ser
    reconhecido como o mesmo "visitante" em requisições futuras,
    dentro da janela de retenção do cookie (ver analytics/config.py).
    """

    return str(uuid.uuid4())


def classificar_origem(referer: str, src_param: str) -> str:
    """
    Classifica a origem do acesso. O parâmetro ?src=qr (adicionado
    pelo próprio sistema nos QR Codes que gera) é a única fonte
    100% confiável — o cabeçalho Referer é só um indício: pode estar
    ausente mesmo quando o clique veio de um app real (o app não
    manda), então nunca é tratado como certeza absoluta.
    """

    if src_param == "qr":
        return "qr"

    if not referer:
        return "direct"

    referer_lower = referer.lower()

    mapa_dominios = (
        ("instagram.com", "instagram"),
        ("wa.me", "whatsapp"),
        ("whatsapp.com", "whatsapp"),
        ("google.", "google"),
        ("facebook.com", "facebook"),
        ("fb.com", "facebook"),
        ("linkedin.com", "linkedin"),
        ("t.co", "twitter"),
        ("twitter.com", "twitter"),
        ("x.com", "twitter"),
        ("tiktok.com", "tiktok"),
    )

    for trecho, origem in mapa_dominios:

        if trecho in referer_lower:
            return origem

    return "unknown"


def registrar_evento_analytics(
    background_tasks,
    card_code: str,
    event_type: str,
    visitor_id: str,
    ip: str,
    user_agent: str,
    referer: str = None,
    src_param: str = None,
    metadata: dict = None
):
    """
    Agenda a gravação do evento numa BackgroundTask do FastAPI — a
    resposta ao visitante (a página HTML, ou o 204 do endpoint de
    clique) é enviada sem esperar esse INSERT terminar, então o
    Analytics nunca deixa o cartão público mais lento. Nenhuma
    infraestrutura nova (fila, worker) é necessária: BackgroundTasks
    já é nativo do FastAPI/Starlette.
    """

    if event_type not in EVENTOS_VALIDOS:
        return

    background_tasks.add_task(
        _gravar_evento,
        card_code, event_type, visitor_id, ip, user_agent, referer, src_param, metadata
    )


def _gravar_evento(card_code, event_type, visitor_id, ip, user_agent, referer, src_param, metadata):
    """
    Executa de fato depois da resposta HTTP já ter sido enviada.
    Qualquer falha aqui é silenciosamente descartada — o Analytics
    nunca pode gerar um erro visível para o visitante nem para o
    fluxo principal do cartão (ver Sprint 28 em diante: o mesmo
    princípio de "nunca quebrar o cartão" já vale para foto/fundo).
    """

    try:

        card_repo = CardRepository()

        try:

            card = card_repo.buscar_por_codigo(card_code)

        finally:

            card_repo.fechar()

        if not card:
            return

        # O IP só existe nesta variável local, usado uma única vez
        # para resolver a localização aproximada — nunca é passado
        # adiante nem gravado em nenhuma coluna do banco.
        country, region, city = geoip.resolver_localizacao(ip)

        repo = AnalyticsRepository()

        try:

            repo.registrar_evento(
                card_id=card.id,
                visitor_id=visitor_id,
                event_type=event_type,
                metadata=metadata,
                country=country,
                region=region,
                city=city,
                device_type=device_parser.detectar_tipo_dispositivo(user_agent),
                os_name=device_parser.detectar_sistema_operacional(user_agent),
                browser_name=device_parser.detectar_navegador(user_agent),
                referrer_source=classificar_origem(referer, src_param)
            )

        finally:

            repo.fechar()

    except Exception:

        pass


def _rotulo_evento(evento_metadata_tupla):

    event_type, metadata = evento_metadata_tupla

    if event_type == "social_link_click" and metadata:
        return metadata.get("label") or _ROTULOS_EVENTO["social_link_click"]

    if event_type == "catalog_item_click" and metadata:
        titulo = metadata.get("title")
        return f"Catálogo — {titulo}" if titulo else "Catálogo"

    return _ROTULOS_EVENTO.get(event_type, event_type)


def _rotular_origens(contagem_por_origem):
    """
    Agrupa por rótulo em vez de por código bruto — "direct" e
    "unknown" (Referer ausente vs. Referer presente mas não
    reconhecido) mostram o mesmo rótulo "Direto/desconhecido" para o
    usuário, mas precisam ser somados antes, senão apareceriam como
    duas linhas idênticas no dashboard.
    """

    agrupado = Counter()

    for origem, total in contagem_por_origem.items():
        agrupado[_ROTULOS_ORIGEM.get(origem, origem)] += total

    return agrupado.most_common()


def _gerar_insights(total_atual, total_anterior, contagem_por_tipo, contagem_por_dispositivo, contagem_por_hora):
    """
    Insights determinísticos (regra simples, sem IA) — só são gerados
    quando há dado suficiente para a frase fazer sentido; não força um
    insight artificial quando o período está vazio.
    """

    insights = []

    if total_anterior > 0:

        variacao = (total_atual - total_anterior) / total_anterior * 100

        if abs(variacao) >= 1:

            direcao = "mais" if variacao > 0 else "menos"
            insights.append(f"Seu cartão recebeu {abs(variacao):.0f}% {direcao} acessos que no período anterior.")

    if contagem_por_tipo:

        tipo_principal, qtd_principal = contagem_por_tipo.most_common(1)[0]

        if qtd_principal > 0:
            insights.append(f"{_ROTULOS_EVENTO.get(tipo_principal, tipo_principal)} foi seu principal canal de interação.")

    if contagem_por_dispositivo:

        total_dispositivos = sum(contagem_por_dispositivo.values())
        mobile = contagem_por_dispositivo.get("mobile", 0)

        if total_dispositivos > 0 and mobile / total_dispositivos >= 0.5:
            insights.append(f"{mobile / total_dispositivos * 100:.0f}% dos acessos vieram de dispositivos móveis.")

    if contagem_por_hora:

        hora_pico = max(contagem_por_hora, key=contagem_por_hora.get)
        insights.append(f"O maior volume de acessos ocorre por volta das {hora_pico}h.")

    return insights


def obter_analytics(owner_id: int, card_code: str = None, periodo: str = "30d"):
    """
    Monta todos os dados agregados do dashboard de Analytics.

    Segurança: sempre parte da lista de cartões que pertencem de fato
    a owner_id (listar_cartoes_por_owner) — um card_code informado que
    não esteja nessa lista nunca é aceito, mesmo que exista no banco e
    pertença a outro usuário. Nunca confia em card_id vindo do
    frontend sem essa checagem.
    """

    cartoes = listar_cartoes_por_owner(owner_id)

    if card_code:

        cartao_selecionado = next((c for c in cartoes if c.code == card_code), None)

        if not cartao_selecionado:
            return {"status": "forbidden"}

        card_ids = [cartao_selecionado.id]

    else:

        card_ids = [c.id for c in cartoes]

    dias = _FILTROS_PERIODO.get(periodo, 30)
    agora = _agora_utc()
    desde_atual = agora - timedelta(days=dias)
    desde_anterior = desde_atual - timedelta(days=dias)

    repo = AnalyticsRepository()

    try:

        # Uma única consulta cobrindo o período atual + o período
        # anterior de mesmo tamanho (para o insight de comparação),
        # dividida em Python — evita uma segunda ida ao banco.
        eventos_brutos = repo.listar_eventos(card_ids, desde_anterior) if card_ids else []

    finally:

        repo.fechar()

    eventos_atuais = [e for e in eventos_brutos if e[10] >= desde_atual]
    eventos_anteriores = [e for e in eventos_brutos if e[10] < desde_atual]

    page_views = [e for e in eventos_atuais if e[0] == "page_view"]
    interacoes = [e for e in eventos_atuais if e[0] != "page_view"]
    page_views_anteriores = [e for e in eventos_anteriores if e[0] == "page_view"]

    total_visualizacoes = len(page_views)
    visitantes_unicos = len({e[1] for e in page_views})
    total_interacoes = len(interacoes)
    taxa_interacao = (total_interacoes / total_visualizacoes * 100) if total_visualizacoes else 0.0

    contagem_por_tipo = Counter(e[0] for e in interacoes)

    interacoes_detalhadas = Counter(_rotulo_evento((e[0], e[2])) for e in interacoes)

    contagem_por_dia = defaultdict(int)

    for e in page_views:
        contagem_por_dia[e[10].date().isoformat()] += 1

    evolucao_diaria = [
        {"data": (desde_atual.date() + timedelta(days=i)).isoformat(), "total": contagem_por_dia.get((desde_atual.date() + timedelta(days=i)).isoformat(), 0)}
        for i in range(dias + 1)
    ]

    contagem_por_hora = defaultdict(int)

    for e in page_views:
        contagem_por_hora[e[10].hour] += 1

    distribuicao_horaria = [{"hora": h, "total": contagem_por_hora.get(h, 0)} for h in range(24)]

    contagem_por_dispositivo = Counter(e[6] for e in page_views if e[6])
    contagem_por_pais = Counter(e[3] for e in page_views if e[3])
    contagem_por_regiao = Counter(e[4] for e in page_views if e[4] and e[3] == "BR")
    contagem_por_origem = Counter(e[9] for e in page_views if e[9])

    total_regiao = sum(contagem_por_regiao.values())

    localizacao_regioes = [
        {"nome": nome, "total": total, "percentual": round(total / total_regiao * 100, 1) if total_regiao else 0}
        for nome, total in contagem_por_regiao.most_common()
    ]

    total_dispositivo = sum(contagem_por_dispositivo.values())

    dispositivos = [
        {"nome": nome, "total": total, "percentual": round(total / total_dispositivo * 100, 1) if total_dispositivo else 0}
        for nome, total in contagem_por_dispositivo.most_common()
    ]

    insights = _gerar_insights(
        total_atual=len(page_views),
        total_anterior=len(page_views_anteriores),
        contagem_por_tipo=contagem_por_tipo,
        contagem_por_dispositivo=contagem_por_dispositivo,
        contagem_por_hora=contagem_por_hora
    )

    return {
        "status": "ok",
        "cartoes": cartoes,
        "card_code_selecionado": card_code,
        "periodo": periodo,
        "periodo_nome": _NOME_FILTRO_PERIODO.get(periodo, periodo),
        "total_visualizacoes": total_visualizacoes,
        "visitantes_unicos": visitantes_unicos,
        "total_interacoes": total_interacoes,
        "taxa_interacao": round(taxa_interacao, 1),
        "evolucao_diaria": evolucao_diaria,
        "distribuicao_horaria": distribuicao_horaria,
        "interacoes_detalhadas": interacoes_detalhadas.most_common(10),
        "regioes": localizacao_regioes,
        "paises": contagem_por_pais.most_common(),
        "dispositivos": dispositivos,
        "origens": _rotular_origens(contagem_por_origem),
        "insights": insights,
        "mapa_estados": montar_mapa_estados(contagem_por_regiao),
        "mapa_grid_cols": GRID_COLS,
        "mapa_grid_rows": GRID_ROWS,
        "tem_dados": len(eventos_atuais) > 0
    }
