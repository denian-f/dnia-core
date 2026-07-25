from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from app.dna_connect.auth.dependencies import get_current_user
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
    current_user=Depends(get_current_user)
):
    """
    Renderiza a página web do Dashboard do usuário autenticado.
    """

    dados = montar_dados_view_dashboard(current_user)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=dados
    )
