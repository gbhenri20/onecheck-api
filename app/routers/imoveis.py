from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models import Endereco, Imovel, ImovelComodo, Usuario
from app.schemas import EnderecoCreate, ImovelCreate, ImovelUpdate, fail, ok
from app.serializers import (
    ensure_default_comodos,
    log_operacao,
    paginate,
    serialize_comodo,
    serialize_endereco,
    serialize_imovel,
)

router = APIRouter(prefix="/imoveis", tags=["imoveis"])


def _apply_endereco(end: Endereco, body: EnderecoCreate, *, is_new: bool) -> None:
    end.rua = body.rua
    end.numero = body.numero
    end.complemento = body.complemento
    end.bairro = body.bairro
    end.cidade = body.cidade
    end.estado = body.estado.upper()
    end.cep = body.cep
    if body.latitude is not None or is_new:
        end.latitude = body.latitude
    if body.longitude is not None or is_new:
        end.longitude = body.longitude


@router.get("")
def list_imoveis(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    status: str | None = None,
    com_endereco: bool = Query(False, description="Inclui endereço com latitude/longitude"),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = db.query(Imovel)
    if com_endereco:
        q = q.options(joinedload(Imovel.endereco))
    if status:
        q = q.filter(Imovel.status == status)
    q = q.order_by(Imovel.created_at.desc())
    items, pag = paginate(q, pagina, por_pagina)
    return ok([serialize_imovel(i, include_endereco=com_endereco) for i in items], pag)


@router.post("")
def create_imovel(
    body: ImovelCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    im = Imovel(
        codigo=body.codigo,
        titulo=body.titulo,
        tipo=body.tipo,
        tamanho=body.tamanho,
        garagem=body.garagem,
        garagem_vagas=body.garagem_vagas,
        status=body.status,
        observacoes=body.observacoes,
    )
    db.add(im)
    db.commit()
    db.refresh(im)
    ensure_default_comodos(db, im.id)
    log_operacao(db, user.id, "create", "imovel", im.id)
    return ok(serialize_imovel(im))


@router.get("/{imovel_id}")
def get_imovel(imovel_id: str, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    im = (
        db.query(Imovel)
        .options(joinedload(Imovel.endereco))
        .filter(Imovel.id == imovel_id)
        .first()
    )
    if not im:
        return fail("Imóvel não encontrado")
    return ok(serialize_imovel(im, include_endereco=True))


@router.put("/{imovel_id}")
def update_imovel(
    imovel_id: str,
    body: ImovelUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    im = db.query(Imovel).filter(Imovel.id == imovel_id).first()
    if not im:
        return fail("Imóvel não encontrado")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(im, field, value)
    db.commit()
    db.refresh(im)
    log_operacao(db, user.id, "update", "imovel", im.id)
    return ok(serialize_imovel(im))


@router.get("/{imovel_id}/endereco")
def get_endereco(imovel_id: str, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    end = db.query(Endereco).filter(Endereco.imovel_id == imovel_id).first()
    if not end:
        return fail("Endereço não encontrado")
    return ok(serialize_endereco(end))


@router.post("/{imovel_id}/endereco")
@router.put("/{imovel_id}/endereco")
@router.patch("/{imovel_id}/endereco")
def upsert_endereco(
    imovel_id: str,
    body: EnderecoCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    im = db.query(Imovel).filter(Imovel.id == imovel_id).first()
    if not im:
        return fail("Imóvel não encontrado")

    end = db.query(Endereco).filter(Endereco.imovel_id == imovel_id).first()
    if end:
        _apply_endereco(end, body, is_new=False)
    else:
        end = Endereco(imovel_id=imovel_id)
        _apply_endereco(end, body, is_new=True)
        db.add(end)
    db.commit()
    db.refresh(end)
    log_operacao(db, user.id, "upsert", "endereco", imovel_id)
    return ok(serialize_endereco(end))


@router.get("/{imovel_id}/comodos")
def list_comodos(imovel_id: str, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    ensure_default_comodos(db, imovel_id)
    comodos = (
        db.query(ImovelComodo)
        .filter(ImovelComodo.imovel_id == imovel_id)
        .order_by(ImovelComodo.tipo)
        .all()
    )
    return ok([serialize_comodo(c) for c in comodos])
