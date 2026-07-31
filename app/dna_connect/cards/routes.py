from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.dna_connect.cards.service import (
    resolver_cartao_publico,
    ativar_cartao,
    atualizar_link_cartao,
    listar_cartoes_por_owner,
    obter_cartao,
    remover_cartao
)
from app.dna_connect.auth.dependencies import get_current_user, get_optional_user

router = APIRouter()

templates = Jinja2Templates(
    directory=[
        str(Path(__file__).resolve().parent / "templates"),
        str(Path(__file__).resolve().parent.parent / "dashboard" / "templates")
    ]
)


def _validar_target_url(target_url: str) -> bool:
    """
    Mesma validação usada pela API: URL obrigatória, iniciando com
    http:// ou https://.
    """

    return bool(target_url) and target_url.startswith(("http://", "https://"))


class ActivateRequest(BaseModel):

    card_code: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "card_code": "TESTE01"
            }
        }
    }


class UpdateCardRequest(BaseModel):

    target_url: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "target_url": "https://instagram.com/denian_df"
            }
        }
    }


@router.get("/c/{card_code}")
def redirect_card(card_code: str, request: Request):
    """
    Resolve o acesso público de um cartão NFC pelo código.

    - Não existe: 404.
    - Existe mas ainda não está configurado: página pública informativa.
    - Existe e está configurado: redireciona (307) para o target_url.
    """

    resultado = resolver_cartao_publico(card_code)

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "unconfigured":

        return templates.TemplateResponse(
            request=request,
            name="card_unconfigured.html",
            context={}
        )

    return RedirectResponse(url=resultado["target_url"], status_code=307)


@router.post("/activate")
def activate_card(
    payload: ActivateRequest,
    current_user=Depends(get_current_user)
):
    """
    Ativa um cartão, associando-o ao usuário autenticado.
    """

    resultado = ativar_cartao(
        email=current_user.email,
        card_code=payload.card_code
    )

    if resultado["status"] == "unauthorized":

        raise HTTPException(
            status_code=401,
            detail="Usuário não encontrado. Cadastre-se em /register antes de ativar um cartão."
        )

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "already_activated":

        raise HTTPException(
            status_code=409,
            detail="Este cartão já está ativado."
        )

    user = resultado["user"]

    return {
        "message": "Cartão ativado com sucesso!",
        "card_code": resultado["card_code"],
        "owner": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }


@router.get("/cards")
def list_my_cards(current_user=Depends(get_current_user)):
    """
    Lista os cartões pertencentes ao usuário autenticado.
    """

    cartoes = listar_cartoes_por_owner(current_user.id)

    return [
        {
            "code": card.code,
            "target_url": card.target_url,
            "activated": card.activated,
            "created_at": card.created_at,
            "updated_at": card.updated_at
        }
        for card in cartoes
    ]


@router.get("/cards/activate")
def activate_card_view(
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Renderiza a tela web de ativação de cartão.
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="activate_card.html",
        context={"erro": None}
    )


@router.post("/cards/activate")
async def activate_card_submit(
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Processa a ativação web de um cartão, reutilizando exatamente o
    mesmo Service de ativação usado pela API (POST /activate).
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    form = await request.form()
    card_code = form.get("card_code", "")

    resultado = ativar_cartao(
        email=current_user.email,
        card_code=card_code
    )

    if resultado["status"] == "unauthorized":

        return templates.TemplateResponse(
            request=request,
            name="activate_card.html",
            context={
                "erro": "Usuário não encontrado. Cadastre-se em /register antes de ativar um cartão."
            },
            status_code=401
        )

    if resultado["status"] == "not_found":

        return templates.TemplateResponse(
            request=request,
            name="activate_card.html",
            context={"erro": "Cartão não encontrado."},
            status_code=404
        )

    if resultado["status"] == "already_activated":

        return templates.TemplateResponse(
            request=request,
            name="activate_card.html",
            context={"erro": "Este cartão já está ativado."},
            status_code=409
        )

    return RedirectResponse(url="/dashboard/view", status_code=302)


@router.get("/cards/{card_code}")
def get_card(
    card_code: str,
    current_user=Depends(get_current_user)
):
    """
    Retorna os detalhes de um cartão pertencente ao usuário autenticado.
    """

    resultado = obter_cartao(
        card_code=card_code,
        owner_id=current_user.id
    )

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para visualizar este cartão."
        )

    card = resultado["card"]

    return {
        "code": card.code,
        "target_url": card.target_url,
        "activated": card.activated,
        "created_at": card.created_at,
        "updated_at": card.updated_at
    }


@router.put("/cards/{card_code}")
def update_card(
    card_code: str,
    payload: UpdateCardRequest,
    current_user=Depends(get_current_user)
):
    """
    Atualiza o link (target_url) de um cartão pertencente ao usuário autenticado.
    """

    if not _validar_target_url(payload.target_url):

        raise HTTPException(
            status_code=400,
            detail="target_url deve ser uma URL válida, iniciando com http:// ou https://."
        )

    resultado = atualizar_link_cartao(
        card_code=card_code,
        owner_id=current_user.id,
        target_url=payload.target_url
    )

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para editar este cartão."
        )

    return {
        "message": "Link do cartão atualizado com sucesso!",
        "card_code": resultado["card_code"],
        "target_url": resultado["target_url"]
    }


@router.get("/cards/{card_code}/edit")
def edit_card_view(
    card_code: str,
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Renderiza a tela web de edição do link de um cartão.
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    resultado = obter_cartao(
        card_code=card_code,
        owner_id=current_user.id
    )

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para editar este cartão."
        )

    return templates.TemplateResponse(
        request=request,
        name="edit_card.html",
        context={
            "cartao": resultado["card"],
            "erro": None,
            "sucesso": None
        }
    )


@router.post("/cards/{card_code}/edit")
async def edit_card_submit(
    card_code: str,
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Processa a edição web do link do cartão, reutilizando exatamente o
    mesmo Service de atualização usado pela API (PUT /cards/{card_code}).
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    form = await request.form()
    target_url = form.get("target_url", "")

    if not _validar_target_url(target_url):

        resultado = obter_cartao(
            card_code=card_code,
            owner_id=current_user.id
        )

        if resultado["status"] == "not_found":
            raise HTTPException(status_code=404, detail="Cartão não encontrado.")

        if resultado["status"] == "forbidden":

            raise HTTPException(
                status_code=403,
                detail="Você não tem permissão para editar este cartão."
            )

        return templates.TemplateResponse(
            request=request,
            name="edit_card.html",
            context={
                "cartao": resultado["card"],
                "erro": "target_url deve ser uma URL válida, iniciando com http:// ou https://.",
                "sucesso": None
            },
            status_code=400
        )

    resultado = atualizar_link_cartao(
        card_code=card_code,
        owner_id=current_user.id,
        target_url=target_url
    )

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para editar este cartão."
        )

    return RedirectResponse(url="/dashboard/view", status_code=302)


@router.post("/cards/{card_code}/remove")
def remove_card(
    card_code: str,
    current_user=Depends(get_optional_user)
):
    """
    Remove a associação do cartão com o usuário autenticado (remoção
    lógica, reutilizando exatamente o Service de remoção).
    """

    if not current_user:
        return RedirectResponse(url="/login/view", status_code=302)

    resultado = remover_cartao(
        card_code=card_code,
        owner_id=current_user.id
    )

    if resultado["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Cartão não encontrado.")

    if resultado["status"] == "forbidden":

        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para remover este cartão."
        )

    return RedirectResponse(url="/dashboard/view", status_code=302)
