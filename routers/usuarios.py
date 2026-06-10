from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import (
    generate_mfa_secret,
    hash_password,
    mfa_provisioning_data,
    verify_password,
    verify_totp_code,
)
from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models import Usuario
from app.schemas import MfaEnableRequest, UsuarioCreate, UsuarioUpdate, UsuarioUpdateMe, fail, ok
from app.serializers import log_operacao, paginate, serialize_usuario

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("/me")
def me(user: Usuario = Depends(get_current_user)):
    return ok(serialize_usuario(user))


@router.patch("/me")
def update_me(
    body: UsuarioUpdateMe,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    if body.nome is not None:
        nome = body.nome.strip()
        if not nome:
            return fail("Nome é obrigatório")
        user.nome = nome

    if body.senha_nova:
        if not body.senha_atual:
            return fail("Informe a senha atual")
        if not verify_password(body.senha_atual, user.senha_hash):
            return fail("Senha atual incorreta")
        user.senha_hash = hash_password(body.senha_nova)

    db.commit()
    db.refresh(user)
    log_operacao(db, user.id, "update", "usuario", user.id, "perfil")
    return ok(serialize_usuario(user))


@router.post("/me/mfa/setup")
def mfa_setup_me(user: Usuario = Depends(get_current_user)):
    secret = generate_mfa_secret()
    return ok(mfa_provisioning_data(user.email, secret))


@router.post("/me/mfa/enable")
def mfa_enable_me(
    body: MfaEnableRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    if not verify_totp_code(body.secret, body.codigo):
        return fail("Código MFA inválido")
    user.mfa_secret = body.secret
    user.mfa_enabled = True
    db.commit()
    db.refresh(user)
    log_operacao(db, user.id, "update", "usuario", user.id, "mfa_enable")
    return ok(serialize_usuario(user))


@router.delete("/me/mfa")
def mfa_disable_me(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    user.mfa_secret = None
    user.mfa_enabled = False
    db.commit()
    db.refresh(user)
    log_operacao(db, user.id, "update", "usuario", user.id, "mfa_disable")
    return ok(serialize_usuario(user))


@router.get("")
def list_usuarios(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    role: str | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = db.query(Usuario).filter(Usuario.ativo == True)
    if role:
        q = q.filter(Usuario.role == role)
    q = q.order_by(Usuario.nome)
    items, pag = paginate(q, pagina, por_pagina)
    return ok([serialize_usuario(u) for u in items], pag)


@router.get("/{usuario_id}")
def get_usuario(
    usuario_id: str,
    db: Session = Depends(get_db),
    current: Usuario = Depends(require_roles("admin", "gestor")),
):
    user = db.query(Usuario).filter(Usuario.id == usuario_id, Usuario.ativo == True).first()
    if not user:
        return fail("Usuário não encontrado")
    return ok(serialize_usuario(user))


@router.put("/{usuario_id}")
def update_usuario(
    usuario_id: str,
    body: UsuarioUpdate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(require_roles("admin", "gestor")),
):
    user = db.query(Usuario).filter(Usuario.id == usuario_id, Usuario.ativo == True).first()
    if not user:
        return fail("Usuário não encontrado")
    if body.nome is not None:
        user.nome = body.nome.strip()
    if body.role is not None:
        user.role = body.role
    if body.mfa_enabled is not None:
        user.mfa_enabled = body.mfa_enabled
        if not body.mfa_enabled:
            user.mfa_secret = None
    if body.senha:
        user.senha_hash = hash_password(body.senha)
    db.commit()
    db.refresh(user)
    log_operacao(db, current.id, "update", "usuario", user.id)
    return ok(serialize_usuario(user))


@router.post("/{usuario_id}/mfa/setup")
def mfa_setup_usuario(
    usuario_id: str,
    db: Session = Depends(get_db),
    current: Usuario = Depends(require_roles("admin", "gestor")),
):
    user = db.query(Usuario).filter(Usuario.id == usuario_id, Usuario.ativo == True).first()
    if not user:
        return fail("Usuário não encontrado")
    secret = generate_mfa_secret()
    return ok(mfa_provisioning_data(user.email, secret))


@router.post("/{usuario_id}/mfa/enable")
def mfa_enable_usuario(
    usuario_id: str,
    body: MfaEnableRequest,
    db: Session = Depends(get_db),
    current: Usuario = Depends(require_roles("admin", "gestor")),
):
    user = db.query(Usuario).filter(Usuario.id == usuario_id, Usuario.ativo == True).first()
    if not user:
        return fail("Usuário não encontrado")
    if not verify_totp_code(body.secret, body.codigo):
        return fail("Código MFA inválido")
    user.mfa_secret = body.secret
    user.mfa_enabled = True
    db.commit()
    db.refresh(user)
    log_operacao(db, current.id, "update", "usuario", user.id, "mfa_enable")
    return ok(serialize_usuario(user))


@router.delete("/{usuario_id}/mfa")
def mfa_reset_usuario(
    usuario_id: str,
    db: Session = Depends(get_db),
    current: Usuario = Depends(require_roles("admin", "gestor")),
):
    user = db.query(Usuario).filter(Usuario.id == usuario_id, Usuario.ativo == True).first()
    if not user:
        return fail("Usuário não encontrado")
    user.mfa_secret = None
    user.mfa_enabled = False
    db.commit()
    db.refresh(user)
    log_operacao(db, current.id, "update", "usuario", user.id, "mfa_reset")
    return ok(serialize_usuario(user))


@router.post("")
def create_usuario(
    body: UsuarioCreate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(require_roles("admin", "gestor")),
):
    if db.query(Usuario).filter(Usuario.email == body.email).first():
        return fail("E-mail já cadastrado")

    user = Usuario(
        nome=body.nome,
        email=body.email,
        senha_hash=hash_password(body.senha),
        role=body.role,
        cpf=body.cpf,
        mfa_enabled=body.role in {"admin", "vistoriador", "gestor"},
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_operacao(db, current.id, "create", "usuario", user.id, body.email)
    return ok(serialize_usuario(user))
