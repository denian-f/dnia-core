from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.dna_connect.auth.dependencies import get_current_admin_web
from app.dna_connect.admin.service import (
    listar_todos_cartoes_admin,
    criar_cartao_admin
)

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)


@router.get("/admin")
def admin_dashboard(
    request: Request,
    current_user=Depends(get_current_admin_web)
):
    """
    Painel administrativo: resumo e listagem de todos os cartões.
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    dados = listar_todos_cartoes_admin()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=dados
    )


@router.get("/admin/cards/new")
def admin_create_card_view(
    request: Request,
    current_user=Depends(get_current_admin_web)
):
    """
    Renderiza o formulário de cadastro de um novo cartão físico.
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="create_card.html",
        context={"erro": None}
    )


@router.post("/admin/cards/new")
async def admin_create_card_submit(
    request: Request,
    current_user=Depends(get_current_admin_web)
):
    """
    Processa o cadastro de um novo cartão, reutilizando o Service
    administrativo específico (que por sua vez reutiliza o CardRepository
    já existente, sem criar uma segunda implementação de acesso a `cards`).
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    form = await request.form()
    card_code = form.get("card_code", "")

    resultado = criar_cartao_admin(card_code)

    if resultado["status"] == "code_required":

        return templates.TemplateResponse(
            request=request,
            name="create_card.html",
            context={"erro": "O código do cartão é obrigatório."},
            status_code=400
        )

    if resultado["status"] == "code_exists":

        return templates.TemplateResponse(
            request=request,
            name="create_card.html",
            context={"erro": "Este código de cartão já existe."},
            status_code=409
        )

    return RedirectResponse(url="/admin", status_code=302)
