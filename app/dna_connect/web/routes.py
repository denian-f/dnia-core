from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.dna_connect.auth.dependencies import get_optional_user
from app.dna_connect.auth.jwt import gerar_token
from app.dna_connect.users.service import (
    autenticar_usuario,
    registrar_usuario,
    confirmar_verificacao_email,
    reenviar_verificacao_email
)

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
        context={"erro": None, "email_nao_verificado": None}
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
            context={"erro": "E-mail ou senha inválidos.", "email_nao_verificado": None},
            status_code=401
        )

    if resultado["status"] == "email_not_verified":

        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "erro": "Você precisa verificar seu e-mail antes de entrar.",
                "email_nao_verificado": email
            },
            status_code=403
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


@router.get("/register/view")
def register_view(
    request: Request,
    current_user=Depends(get_optional_user)
):
    """
    Renderiza a página pública de cadastro. Se já autenticado, segue
    direto ao Dashboard (mesmo padrão de /login/view).
    """

    if current_user:
        return RedirectResponse(url="/dashboard/view", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"erro": None}
    )


@router.post("/register/view")
async def register_submit(request: Request):
    """
    Processa o cadastro web reaproveitando exatamente o mesmo Service de
    cadastro já usado pela API (POST /register). Não autentica
    automaticamente: o fluxo redireciona para /login/view.
    """

    form = await request.form()

    name = form.get("name", "")
    email = form.get("email", "")
    password = form.get("password", "")
    confirm_password = form.get("confirm_password", "")

    if not name or not email or not password or not confirm_password:

        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"erro": "Todos os campos são obrigatórios."},
            status_code=400
        )

    if password != confirm_password:

        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"erro": "As senhas não coincidem."},
            status_code=400
        )

    resultado = registrar_usuario(
        name=name,
        email=email,
        password=password
    )

    if resultado["status"] == "email_exists":

        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"erro": "Este e-mail já está cadastrado."},
            status_code=409
        )

    return RedirectResponse(
        url=f"/verify-email/pending?email={quote(email)}",
        status_code=302
    )


@router.get("/verify-email/pending")
def verify_email_pending_view(request: Request, email: str = ""):
    """
    Página pública informando que é necessário verificar o e-mail
    antes de acessar a conta.
    """

    return templates.TemplateResponse(
        request=request,
        name="verify_email_pending.html",
        context={"email": email, "mensagem": None}
    )


@router.post("/verify-email/resend")
async def verify_email_resend(request: Request):
    """
    Reenvia o e-mail de verificação, reutilizando exatamente o Service
    de reenvio (que já aplica cooldown e nunca revela se a conta existe).
    """

    form = await request.form()
    email = form.get("email", "")

    if email:
        reenviar_verificacao_email(email)

    return templates.TemplateResponse(
        request=request,
        name="verify_email_pending.html",
        context={
            "email": email,
            "mensagem": (
                "Se existir uma conta pendente de verificação para este "
                "e-mail, enviaremos uma nova mensagem em instantes."
            )
        }
    )


@router.get("/verify-email")
def verify_email_confirm(request: Request, token: str = ""):
    """
    Confirma um token de verificação de e-mail, reutilizando exatamente
    o Service responsável pela regra de negócio.
    """

    resultado = confirmar_verificacao_email(token)

    if resultado["status"] != "verified":

        return templates.TemplateResponse(
            request=request,
            name="verify_email_invalid.html",
            context={}
        )

    return templates.TemplateResponse(
        request=request,
        name="verify_email_success.html",
        context={}
    )
