from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import (
    AgendamentoVistoria,
    Checklist,
    Contrato,
    Imovel,
    LogOperacao,
    Problema,
    Usuario,
)
from app.schemas import ok
from app.serializers import paginate

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    imoveis_locados = db.query(Imovel).filter(Imovel.status == "locado").count()
    checklists_pendentes = (
        db.query(Checklist)
        .filter(Checklist.status.in_(["pendente_aceite", "pendente_revisao"]))
        .count()
    )
    problemas_abertos = db.query(Problema).filter(Problema.status == "aberto").count()
    vistorias_agendadas = db.query(AgendamentoVistoria).count()

    return ok({
        "imoveis_locados": imoveis_locados,
        "checklists_pendentes": checklists_pendentes,
        "problemas_abertos": problemas_abertos,
        "vistorias_agendadas": vistorias_agendadas,
    })


@router.get("/logs")
def logs(
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = db.query(LogOperacao).order_by(LogOperacao.created_at.desc())
    items, pag = paginate(q, pagina, por_pagina)
    return ok([
        {
            "id": l.id,
            "usuario_id": l.usuario_id,
            "acao": l.acao,
            "entidade": l.entidade,
            "entidade_id": l.entidade_id,
            "detalhes": l.detalhes,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in items
    ], pag)
