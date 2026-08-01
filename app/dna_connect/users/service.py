import re
import secrets
import hashlib
from datetime import datetime, timedelta, timezone

from app.dna_connect.users.repository import UserRepository
from app.security.hashing import hash_password, verify_password
from app.dna_connect.email.service import enviar_email
from app.dna_connect.email import config as email_config

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def init_users_db():
    """
    Garante a existência da tabela de usuários e das colunas de senha,
    administração e verificação de e-mail.
    """

    repo = UserRepository()

    try:

        repo.criar_tabela()
        repo.adicionar_coluna_senha()
        repo.adicionar_coluna_is_admin()
        repo.adicionar_colunas_verificacao_email()

    finally:

        repo.fechar()


def _agora_utc():
    """
    Retorna o horário atual em UTC, sem tzinfo, para comparação direta
    com os valores (naive) devolvidos pelo psycopg para colunas TIMESTAMP.
    """

    return datetime.now(timezone.utc).replace(tzinfo=None)


def _gerar_token_verificacao():
    """
    Gera um token de verificação criptograficamente seguro e o hash
    (SHA-256) que será persistido. O token original nunca é armazenado.
    """

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    return token, token_hash


def _montar_email_verificacao(name: str, token: str):

    link = f"{email_config.APP_BASE_URL}/verify-email?token={token}"

    texto = (
        f"Olá, {name}.\n\n"
        "Obrigado por criar sua conta no DNA Connect.\n\n"
        "Para confirmar seu e-mail e acessar sua conta, acesse o link abaixo:\n"
        f"{link}\n\n"
        "Este link expira em 24 horas.\n\n"
        "Se você não criou esta conta, ignore esta mensagem.\n\n"
        "DNA Connect"
    )

    html = f"""
        <p>Olá, {name}.</p>
        <p>Obrigado por criar sua conta no DNA Connect.</p>
        <p>Para confirmar seu e-mail e acessar sua conta, clique no botão abaixo:</p>
        <p>
            <a href="{link}"
               style="display:inline-block;padding:10px 16px;background-color:#111827;
                      color:#ffffff;text-decoration:none;border-radius:4px;">
                Verificar meu e-mail
            </a>
        </p>
        <p>Ou copie e cole este link no navegador:<br>{link}</p>
        <p>Este link expira em 24 horas.</p>
        <p>Se você não criou esta conta, ignore esta mensagem.</p>
        <p>DNA Connect</p>
    """

    return texto, html


def enviar_verificacao_email(user):
    """
    Gera um novo token de verificação para o usuário (invalidando
    qualquer token anterior), salva apenas o hash e a expiração, e
    envia o e-mail de verificação pela Brevo.
    """

    token, token_hash = _gerar_token_verificacao()

    expira_em = _agora_utc() + timedelta(
        hours=email_config.EMAIL_VERIFICATION_EXPIRATION_HOURS
    )

    repo = UserRepository()

    try:

        repo.definir_token_verificacao(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expira_em
        )

    finally:

        repo.fechar()

    texto, html = _montar_email_verificacao(user.name, token)

    return enviar_email(
        destinatario=user.email,
        assunto="Confirme seu e-mail - DNA Connect",
        conteudo_html=html,
        conteudo_texto=texto
    )


def confirmar_verificacao_email(token: str):
    """
    Confirma um token de verificação de e-mail: localiza o usuário pelo
    hash do token, valida a expiração, marca a conta como verificada e
    invalida o token (uso único).
    """

    if not token:
        return {"status": "invalid"}

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    repo = UserRepository()

    try:

        user = repo.buscar_por_token_hash(token_hash)

        if not user:
            return {"status": "invalid"}

        if not user.email_verification_expires_at:
            return {"status": "invalid"}

        if user.email_verification_expires_at < _agora_utc():
            return {"status": "expired"}

        repo.marcar_email_verificado(user_id=user.id)

    finally:

        repo.fechar()

    return {"status": "verified", "user": user}


def reenviar_verificacao_email(email: str):
    """
    Reenvia o e-mail de verificação, respeitando um cooldown simples
    contra reenvios excessivos. A resposta é sempre a mesma
    independentemente do e-mail existir, já estar verificado ou estar
    em cooldown, para evitar enumeração de contas.
    """

    user = buscar_usuario_por_email(email)

    if not user or user.email_verified:
        return {"status": "ok"}

    if user.email_verification_last_sent_at:

        cooldown_ate = user.email_verification_last_sent_at + timedelta(
            seconds=email_config.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS
        )

        if _agora_utc() < cooldown_ate:
            return {"status": "ok"}

    enviar_verificacao_email(user)

    return {"status": "ok"}


def buscar_usuario_por_email(email: str):
    """
    Retorna o usuário com o e-mail informado, ou None caso não exista.
    """

    repo = UserRepository()

    try:

        return repo.buscar_por_email(email)

    finally:

        repo.fechar()


def registrar_usuario(name: str, email: str, password: str):
    """
    Cria uma conta permanente, com senha, para um novo usuário.
    """

    repo = UserRepository()

    try:

        existente = repo.buscar_por_email(email)

        if existente:
            return {"status": "email_exists"}

        password_hash = hash_password(password)

        user = repo.criar_usuario(
            name=name,
            email=email,
            password_hash=password_hash
        )

    finally:

        repo.fechar()

    # A conta já existe mesmo que o envio do e-mail falhe; o usuário
    # permanece não verificado e pode solicitar reenvio depois.
    enviar_verificacao_email(user)

    return {"status": "created", "user": user}


def autenticar_usuario(email: str, password: str):
    """
    Valida e-mail e senha de um usuário. Contas com e-mail ainda não
    verificado não podem autenticar.
    """

    user = buscar_usuario_por_email(email)

    if not user or not user.password_hash:
        return {"status": "invalid_credentials"}

    if not verify_password(password, user.password_hash):
        return {"status": "invalid_credentials"}

    if not user.email_verified:
        return {"status": "email_not_verified"}

    return {"status": "authenticated", "user": user}


def listar_cartoes_do_usuario(email: str):
    """
    Retorna os cartões pertencentes ao usuário com o e-mail informado.
    """

    user = buscar_usuario_por_email(email)

    if not user:
        return {"status": "not_found"}

    # Import local para evitar importação circular
    from app.dna_connect.cards.service import listar_cartoes_por_owner

    cartoes = listar_cartoes_por_owner(user.id)

    return {"status": "ok", "cartoes": cartoes}


def _email_valido(email: str) -> bool:

    return bool(email) and bool(EMAIL_REGEX.match(email))


def atualizar_perfil_usuario(user_id: int, name: str, email: str):
    """
    Atualiza nome e e-mail do usuário autenticado.
    """

    if not name:
        return {"status": "name_required"}

    if not email:
        return {"status": "email_required"}

    if not _email_valido(email):
        return {"status": "invalid_email"}

    repo = UserRepository()

    try:

        existente = repo.buscar_por_email(email)

        if existente and existente.id != user_id:
            return {"status": "email_exists"}

        user = repo.atualizar_perfil(
            user_id=user_id,
            name=name,
            email=email
        )

    finally:

        repo.fechar()

    return {"status": "updated", "user": user}


def alterar_senha_usuario(
    user_id: int,
    senha_atual: str,
    nova_senha: str,
    confirmar_senha: str
):
    """
    Altera a senha do usuário autenticado, reutilizando o hashing
    já existente (app.security.hashing) para validar e gerar o hash.
    """

    if not senha_atual:
        return {"status": "current_password_required"}

    if not nova_senha:
        return {"status": "new_password_required"}

    if not confirmar_senha:
        return {"status": "confirmation_required"}

    if nova_senha != confirmar_senha:
        return {"status": "password_mismatch"}

    repo = UserRepository()

    try:

        user = repo.buscar_por_id(user_id)

        if not user or not user.password_hash:
            return {"status": "invalid_current_password"}

        if not verify_password(senha_atual, user.password_hash):
            return {"status": "invalid_current_password"}

        if verify_password(nova_senha, user.password_hash):
            return {"status": "same_password"}

        novo_hash = hash_password(nova_senha)

        repo.atualizar_senha(
            user_id=user_id,
            password_hash=novo_hash
        )

    finally:

        repo.fechar()

    return {"status": "updated"}


def promover_usuario_admin(email: str):
    """
    Concede permissão administrativa a um usuário já existente. Nunca
    cria um usuário novo; operação idempotente.
    """

    repo = UserRepository()

    try:

        user = repo.buscar_por_email(email)

        if not user:
            return {"status": "not_found"}

        repo.promover_admin(user_id=user.id)

    finally:

        repo.fechar()

    return {"status": "promoted"}
