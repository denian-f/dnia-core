from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.dna_connect.auth.dependencies import get_optional_user
from app.dna_connect.auth.jwt import gerar_token
from app.dna_connect.users.service import autenticar_usuario

router = APIRouter()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)


@router.get("/login/view")
def login_view(
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Renderiza a página de login. Se já autenticado, segue direto ao Dashboard.
    """

    if current_user:
        return RedirectResponse(url="/dashboard/view", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"erro": None}
    )


@router.post("/login/view")
async def login_submit(request: Request):
    """
    Processa o login web reaproveitando o mesmo Service de autenticação
    e o mesmo JWT já utilizados pela API, salvando o token num Cookie
    HttpOnly em vez de devolvê-lo no corpo da resposta.
    """

    form = await request.form()

    email = form.get("email", "")
    password = form.get("password", "")

    resultado = autenticar_usuario(
        email=email,
        password=password
    )

    if resultado["status"] == "invalid_credentials":

        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"erro": "E-mail ou senha inválidos."},
            status_code=401
        )

    user = resultado["user"]

    access_token = gerar_token(
        user_id=user.id,
        email=user.email
    )

    response = RedirectResponse(url="/dashboard/view", status_code=302)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax"
    )

    return response


@router.post("/logout")
def logout():
    """
    Remove o Cookie de autenticação e volta para a tela de login.
    """

    response = RedirectResponse(url="/login/view", status_code=302)
    response.delete_cookie("access_token")

    return response
