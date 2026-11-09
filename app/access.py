"""Regras de acesso do OneCheck.

O papel no token não autoriza a operação sozinho: cada consulta de contrato,
imóvel ou conta passa por estas funções. `require_roles` continua sendo a
barreira das rotas administrativas.
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Checklist, Contrato, Usuario

OPERACAO = ("admin", "gestor")
RESUMO_OPERACIONAL = ("vistoriador", "locatario")


def assert_pode_ver_contrato(
    db: Session,
    contrato: Contrato,
    user: Usuario,
    *,
    permitir_locatario: bool = True,
) -> None:
    if user.role in OPERACAO:
        return
    if user.role == "locatario":
        if permitir_locatario and contrato.locatario_id == user.id:
            return
        raise HTTPException(status_code=403, detail="Sem permissão para acessar este contrato")
    if user.role == "vistoriador" and _vistoriador_no_contrato(db, user.id, contrato.id):
        return
    raise HTTPException(status_code=403, detail="Sem permissão para acessar este contrato")


def assert_pode_ver_imovel(db: Session, imovel_id: str, user: Usuario) -> None:
    if user.role in OPERACAO:
        return
    if user.role == "locatario":
        proprio = (
            db.query(Contrato.id)
            .filter(
                Contrato.imovel_id == imovel_id,
                Contrato.locatario_id == user.id,
                Contrato.status == "ativo",
            )
            .first()
        )
        if proprio:
            return
        raise HTTPException(status_code=403, detail="Você não tem acesso a este imóvel")
    if user.role == "vistoriador" and _vistoriador_no_imovel(db, user.id, imovel_id):
        return
    raise HTTPException(status_code=403, detail="Você não tem acesso a este imóvel")


def _vistoriador_no_contrato(db: Session, usuario_id: str, contrato_id: str) -> bool:
    return (
        db.query(Checklist.id)
        .filter(
            Checklist.contrato_id == contrato_id,
            Checklist.vistoriador_id == usuario_id,
        )
        .first()
        is not None
    )


def _vistoriador_no_imovel(db: Session, usuario_id: str, imovel_id: str) -> bool:
    return (
        db.query(Checklist.id)
        .join(Contrato, Contrato.id == Checklist.contrato_id)
        .filter(
            Contrato.imovel_id == imovel_id,
            Checklist.vistoriador_id == usuario_id,
        )
        .first()
        is not None
    )
