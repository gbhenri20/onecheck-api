from datetime import date, datetime

from sqlalchemy.orm import Session

from app.config import PUBLIC_BASE_URL
from app.models import (
    Checklist,
    ChecklistItem,
    ChecklistItemFoto,
    Contrato,
    Endereco,
    Imovel,
    ImovelComodo,
    ItemVistoria,
    LogOperacao,
    Usuario,
)


def foto_url(arquivo: str) -> str:
    path = f"/api/v1/uploads/{arquivo}"
    return path


def serialize_foto(f: ChecklistItemFoto) -> dict:
    return {"id": f.id, "url": foto_url(f.arquivo)}


def serialize_item(item: ChecklistItem) -> dict:
    return {
        "id": item.id,
        "checklist_id": item.checklist_id,
        "comodo_id": item.comodo_id,
        "item_vistoria_id": item.item_vistoria_id,
        "estado": item.estado,
        "observacao": item.observacao,
        "fotos": [serialize_foto(f) for f in item.fotos],
    }


def serialize_comodo(c: ImovelComodo) -> dict:
    return {
        "id": c.id,
        "imovel_id": c.imovel_id,
        "tipo": c.tipo,
        "descricao": c.descricao,
        "nome": c.nome,
    }


def serialize_checklist(
    ck: Checklist,
    include_itens: bool = False,
    comodos: list[ImovelComodo] | None = None,
) -> dict:
    data = {
        "id": ck.id,
        "contrato_id": ck.contrato_id,
        "vistoriador_id": ck.vistoriador_id,
        "tipo": ck.tipo,
        "status": ck.status,
        "data_vistoria": ck.data_vistoria.isoformat() if ck.data_vistoria else None,
        "created_at": ck.created_at.isoformat() if ck.created_at else None,
    }
    if include_itens:
        data["itens"] = [serialize_item(i) for i in ck.itens]
    if comodos is not None:
        data["comodos"] = [serialize_comodo(c) for c in comodos]
    return data


def serialize_endereco(end: Endereco | None) -> dict | None:
    if not end:
        return None
    return {
        "rua": end.rua,
        "logradouro": end.rua,
        "numero": end.numero,
        "complemento": end.complemento,
        "bairro": end.bairro,
        "cidade": end.cidade,
        "estado": end.estado,
        "cep": end.cep,
        "latitude": end.latitude,
        "longitude": end.longitude,
    }


def serialize_imovel(im: Imovel, *, include_endereco: bool = False) -> dict:
    data = {
        "id": im.id,
        "codigo": im.codigo,
        "titulo": im.titulo,
        "tipo": im.tipo,
        "tamanho": im.tamanho,
        "garagem": im.garagem,
        "garagem_vagas": im.garagem_vagas,
        "status": im.status,
        "observacoes": im.observacoes,
        "created_at": im.created_at.isoformat() if im.created_at else None,
    }
    if include_endereco:
        end = im.endereco if hasattr(im, "endereco") else None
        data["endereco"] = serialize_endereco(end)
    return data


def serialize_contrato(ct: Contrato) -> dict:
    return {
        "id": ct.id,
        "imovel_id": ct.imovel_id,
        "locatario_id": ct.locatario_id,
        "data_inicio": ct.data_inicio.isoformat(),
        "data_fim": ct.data_fim.isoformat(),
        "valor_mensal": float(ct.valor_mensal) if ct.valor_mensal is not None else None,
        "status": ct.status,
        "created_at": ct.created_at.isoformat() if ct.created_at else None,
    }


def serialize_usuario(u: Usuario) -> dict:
    return {
        "id": u.id,
        "nome": u.nome,
        "email": u.email,
        "role": u.role,
        "cpf": u.cpf,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


def paginate(query, pagina: int, por_pagina: int):
    total = query.count()
    items = query.offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    return items, {
        "total": total,
        "pagina": pagina,
        "itensPorPagina": por_pagina,
    }


def log_operacao(
    db: Session,
    usuario_id: str | None,
    acao: str,
    entidade: str | None = None,
    entidade_id: str | None = None,
    detalhes: str | None = None,
) -> None:
    db.add(
        LogOperacao(
            usuario_id=usuario_id,
            acao=acao,
            entidade=entidade,
            entidade_id=entidade_id,
            detalhes=detalhes,
        )
    )
    db.commit()


def get_comodos_for_checklist(db: Session, checklist: Checklist) -> list[ImovelComodo]:
    contrato = db.query(Contrato).filter(Contrato.id == checklist.contrato_id).first()
    if not contrato:
        return []
    return (
        db.query(ImovelComodo)
        .filter(ImovelComodo.imovel_id == contrato.imovel_id)
        .order_by(ImovelComodo.tipo)
        .all()
    )


def ensure_default_comodos(db: Session, imovel_id: str) -> None:
    existing = db.query(ImovelComodo).filter(ImovelComodo.imovel_id == imovel_id).count()
    if existing > 0:
        return
    defaults = [
        ("Sala", "sala"),
        ("Cozinha", "cozinha"),
        ("Quarto 1", "quarto"),
        ("Banheiro", "banheiro"),
    ]
    for nome, tipo in defaults:
        db.add(ImovelComodo(imovel_id=imovel_id, tipo=tipo, nome=nome, descricao=nome))
    db.commit()
