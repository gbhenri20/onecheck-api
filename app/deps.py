from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth import decode_token
from app.database import get_db
from app.models import Usuario

security = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> Usuario:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=401, detail="Token ausente")
    payload = decode_token(creds.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token inválido")
    user = db.query(Usuario).filter(Usuario.id == payload["sub"], Usuario.ativo == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return user


def require_roles(*roles: str):
    def _dep(user: Usuario = Depends(get_current_user)) -> Usuario:
        if user.role not in roles and user.role != "admin":
            raise HTTPException(status_code=403, detail="Permissão negada")
        return user

    return _dep
