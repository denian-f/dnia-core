from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.dna_connect.auth.dependencies import get_current_user, get_optional_user
from app.dna_connect.dashboard.service import (
    obter_resumo_dashboard,
    montar_dados_view_dashboard
)

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)


@router.get("/dashboard")
def get_dashboard(current_user=Depends(get_current_user)):
    """
    Retorna o resumo do Dashboard do usuário autenticado.
    """

    return obter_resumo_dashboard(current_user)


@router.get("/dashboard/view")
def view_dashboard(
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Renderiza a página web do Dashboard do usuário autenticado.
    Sem autenticação (Bearer ou Cookie), redireciona para a tela de login.
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    dados = montar_dados_view_dashboard(current_user)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=dados
    )
