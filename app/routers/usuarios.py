from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models import Usuario
from app.schemas import UsuarioCreate, fail, ok
from app.serializers import log_operacao, paginate, serialize_usuario

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("/me")
def me(user: Usuario = Depends(get_current_user)):
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
