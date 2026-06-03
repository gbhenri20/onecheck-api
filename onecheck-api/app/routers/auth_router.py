from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    create_refresh_token,
    create_temp_token,
    decode_token,
    hash_password,
    needs_mfa,
    revoke_refresh_token,
    usuario_to_dict,
    verify_password,
    verify_refresh_token,
    verify_totp,
)
from app.database import get_db
from app.deps import get_current_user
from app.models import Usuario
from app.schemas import LoginRequest, MfaVerifyRequest, RefreshRequest, fail, ok
from app.serializers import log_operacao

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == body.email, Usuario.ativo == True).first()
    if not user or not verify_password(body.senha, user.senha_hash):
        return fail("Credenciais inválidas")

    if needs_mfa(user):
        temp = create_temp_token(user.id)
        return ok({
            "mfa_required": True,
            "temp_token": temp,
            "mfa_token": temp,
        })

    access = create_access_token(user.id, user.role)
    refresh = create_refresh_token(db, user.id)
    log_operacao(db, user.id, "login", "usuario", user.id)
    return ok({
        "access_token": access,
        "refresh_token": refresh,
        "usuario": usuario_to_dict(user),
    })


@router.post("/mfa/verify")
def mfa_verify(body: MfaVerifyRequest, db: Session = Depends(get_db)):
    payload = decode_token(body.temp_token)
    if not payload or payload.get("type") != "mfa":
        return fail("Token MFA inválido ou expirado")

    user = db.query(Usuario).filter(Usuario.id == payload["sub"], Usuario.ativo == True).first()
    if not user:
        return fail("Usuário não encontrado")

    if not verify_totp(user, body.codigo.strip()):
        return fail("Código MFA inválido")

    access = create_access_token(user.id, user.role)
    refresh = create_refresh_token(db, user.id)
    log_operacao(db, user.id, "mfa_verify", "usuario", user.id)
    return ok({
        "access_token": access,
        "refresh_token": refresh,
        "usuario": usuario_to_dict(user),
    })


@router.post("/refresh")
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    user = verify_refresh_token(db, body.refresh_token)
    if not user:
        return fail("Refresh token inválido ou expirado")

    access = create_access_token(user.id, user.role)
    new_refresh = create_refresh_token(db, user.id)
    revoke_refresh_token(db, body.refresh_token)
    return ok({"access_token": access, "refresh_token": new_refresh})


@router.post("/logout")
def logout(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    body: RefreshRequest | None = None,
):
    if body is not None and body.refresh_token:
        revoke_refresh_token(db, body.refresh_token)
    log_operacao(db, user.id, "logout", "usuario", user.id)
    return ok(None)
