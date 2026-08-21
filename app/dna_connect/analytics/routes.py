from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.dna_connect.auth.dependencies import get_optional_user
from app.dna_connect.analytics.service import (
    obter_analytics,
    registrar_evento_analytics,
    gerar_visitor_id
)
from app.dna_connect.analytics import config as analytics_config

router = APIRouter()

templates = Jinja2Templates(
    directory=[
        str(Path(__file__).resolve().parent / "templates"),
        str(Path(__file__).resolve().parent.parent / "dashboard" / "templates")
    ]
)

_COOKIE_VISITOR_ID = "dna_visitor_id"


def obter_ip_cliente(request: Request):
    """
    Prioriza X-Forwarded-For (o app roda atrás de proxy no Render) —
    usa só o primeiro IP da cadeia (o do cliente real). Esse valor
    passa exclusivamente pela resolução de geolocalização (ver
    analytics/geoip.py) e nunca é gravado em nenhuma coluna do banco.
    """

    encaminhado = request.headers.get("x-forwarded-for")

    if encaminhado:
        return encaminhado.split(",")[0].strip()

    return request.client.host if request.client else None


def obter_ou_criar_visitor_id(request: Request):
    """
    Retorna (visitor_id, precisa_definir_cookie). Reaproveita o cookie
    existente quando presente — é assim que um "visitante recorrente"
    é reconhecido (mesmo navegador voltando dentro da janela de
    retenção), sem nenhuma relação com a identidade da pessoa.
    """

    existente = request.cookies.get(_COOKIE_VISITOR_ID)

    if existente:
        return existente, False

    return gerar_visitor_id(), True


def definir_cookie_visitor(response, visitor_id: str):

    response.set_cookie(
        key=_COOKIE_VISITOR_ID,
        value=visitor_id,
        max_age=analytics_config.VISITOR_COOKIE_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax"
    )


@router.post("/c/{card_code}/track")
async def track_event(card_code: str, request: Request, background_tasks: BackgroundTasks):
    """
    Recebe eventos de clique/interação da página pública do cartão,
    enviados via navigator.sendBeacon — não bloqueia a navegação do
    visitante, mesmo quando o clique já está levando a outro site (ex:
    abrir o WhatsApp). Sempre responde rápido (204); a gravação roda
    depois, numa BackgroundTask (ver registrar_evento_analytics).
    """

    try:

        corpo = await request.json()

    except Exception:

        corpo = {}

    event_type = corpo.get("event_type") if isinstance(corpo, dict) else None
    metadata = corpo.get("metadata") if isinstance(corpo, dict) else None

    visitor_id, precisa_definir_cookie = obter_ou_criar_visitor_id(request)

    if event_type:

        registrar_evento_analytics(
            background_tasks=background_tasks,
            card_code=card_code,
            event_type=event_type,
            visitor_id=visitor_id,
            ip=obter_ip_cliente(request),
            user_agent=request.headers.get("user-agent"),
            referer=request.headers.get("referer"),
            src_param=request.query_params.get("src"),
            metadata=metadata if isinstance(metadata, dict) else None
        )

    resposta = Response(status_code=204)

    if precisa_definir_cookie:
        definir_cookie_visitor(resposta, visitor_id)

    return resposta


@router.get("/analytics")
def view_analytics(
    request: Request,
    card: str = None,
    periodo: str = "30d",
    current_user=Depends(get_optional_user)
):
    """
    Dashboard de Analytics — exige autenticação. `card` (opcional)
    filtra por um único cartão; sem ele, agrega todos os cartões do
    usuário. Um card_code que não pertença ao usuário autenticado
    nunca é aceito (ver obter_analytics) — nesse caso a página cai de
    volta para "todos os cartões" em vez de vazar qualquer dado de
    outro usuário ou retornar erro.
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    resultado = obter_analytics(owner_id=current_user.id, card_code=card, periodo=periodo)

    if resultado["status"] == "forbidden":
        resultado = obter_analytics(owner_id=current_user.id, card_code=None, periodo=periodo)

    return templates.TemplateResponse(
        request=request,
        name="analytics.html",
        context=resultado
    )
