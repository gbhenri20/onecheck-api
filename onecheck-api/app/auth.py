import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import pyotp
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import (
    JWT_ACCESS_MINUTES,
    JWT_ALGORITHM,
    JWT_REFRESH_DAYS,
    JWT_SECRET,
)
from app.models import RefreshToken, Usuario

MFA_REQUIRED_ROLES = {"admin", "vistoriador", "gestor"}


def hash_password(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def verify_password(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode(), senha_hash.encode())
    except ValueError:
        return False


def create_access_token(usuario_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_MINUTES)
    payload = {"sub": usuario_id, "role": role, "type": "access", "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_temp_token(usuario_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    payload = {"sub": usuario_id, "type": "mfa", "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


def _hash_refresh(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_refresh_token(db: Session, usuario_id: str) -> str:
    raw = secrets.token_urlsafe(48)
    token = RefreshToken(
        usuario_id=usuario_id,
        token_hash=_hash_refresh(raw),
        expires_at=datetime.utcnow() + timedelta(days=JWT_REFRESH_DAYS),
    )
    db.add(token)
    db.commit()
    return raw


def verify_refresh_token(db: Session, raw: str) -> Usuario | None:
    h = _hash_refresh(raw)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == h).first()
    if not row or row.expires_at < datetime.utcnow():
        return None
    return db.query(Usuario).filter(Usuario.id == row.usuario_id, Usuario.ativo == True).first()


def revoke_refresh_token(db: Session, raw: str) -> None:
    h = _hash_refresh(raw)
    db.query(RefreshToken).filter(RefreshToken.token_hash == h).delete()
    db.commit()


def needs_mfa(user: Usuario) -> bool:
    return user.role in MFA_REQUIRED_ROLES and user.mfa_enabled


def verify_totp(user: Usuario, codigo: str) -> bool:
    if not user.mfa_secret:
        return False
    totp = pyotp.TOTP(user.mfa_secret)
    return totp.verify(codigo, valid_window=1)


def generate_mfa_secret() -> str:
    return pyotp.random_base32()


def usuario_to_dict(user: Usuario) -> dict:
    return {
        "id": user.id,
        "nome": user.nome,
        "email": user.email,
        "role": user.role,
    }
