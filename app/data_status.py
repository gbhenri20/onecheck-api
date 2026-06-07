"""Totais atuais do banco (somente leitura)."""
from sqlalchemy.orm import Session

from app.models import (
    AgendamentoVistoria,
    Checklist,
    Contrato,
    Endereco,
    Imovel,
    ItemVistoria,
    Problema,
    Usuario,
)


def get_data_status(db: Session) -> dict:
    enderecos_com_coords = (
        db.query(Endereco)
        .filter(Endereco.latitude.isnot(None), Endereco.longitude.isnot(None))
        .count()
    )
    return {
        "usuarios": db.query(Usuario).count(),
        "imoveis": db.query(Imovel).count(),
        "enderecos": db.query(Endereco).count(),
        "enderecos_com_coordenadas": enderecos_com_coords,
        "contratos": db.query(Contrato).count(),
        "checklists": db.query(Checklist).count(),
        "agendamentos": db.query(AgendamentoVistoria).count(),
        "problemas": db.query(Problema).count(),
        "itens_vistoria": db.query(ItemVistoria).count(),
        "checklists_por_status": {
            status: db.query(Checklist).filter(Checklist.status == status).count()
            for status in ("em_preenchimento", "pendente_aceite", "aceito", "rejeitado", "pendente_revisao")
        },
    }
