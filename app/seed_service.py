"""Seed completo + modo expand para enriquecer banco existente."""
from datetime import date, timedelta

import pyotp
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models import (
    AgendamentoVistoria,
    Checklist,
    ChecklistItem,
    ChecklistItemFoto,
    Contrato,
    Endereco,
    Imovel,
    ImovelComodo,
    ItemVistoria,
    LogOperacao,
    Problema,
    RefreshToken,
    Usuario,
)
from app.serializers import ensure_default_comodos, log_operacao

MFA_SECRET = "JBSWY3DPEHPK3PXP"


def _clear_all(db: Session) -> None:
    db.query(ChecklistItemFoto).delete()
    db.query(ChecklistItem).delete()
    db.query(Checklist).delete()
    db.query(AgendamentoVistoria).delete()
    db.query(Problema).delete()
    db.query(Contrato).delete()
    db.query(Endereco).delete()
    db.query(ImovelComodo).delete()
    db.query(Imovel).delete()
    db.query(ItemVistoria).delete()
    db.query(LogOperacao).delete()
    db.query(RefreshToken).delete()
    db.query(Usuario).delete()
    db.commit()


def _create_imovel_com_contrato(
    db: Session,
    *,
    codigo: str,
    titulo: str,
    tipo: str,
    tamanho: str,
    status_final: str,
    endereco: dict,
    locatario_id: str,
    vistoriador_id: str,
    valor: float,
    checklist_tipo: str = "inicial",
    checklist_status: str = "em_preenchimento",
    dias_contrato: int = 365,
    offset_dias: int = 0,
    problemas: list[dict] | None = None,
    preencher_itens: bool = False,
) -> dict:
    hoje = date.today() + timedelta(days=offset_dias)
    im = Imovel(
        codigo=codigo,
        titulo=titulo,
        tipo=tipo,
        tamanho=tamanho,
        garagem=True,
        garagem_vagas=1,
        status="disponivel",
    )
    db.add(im)
    db.flush()
    ensure_default_comodos(db, im.id)
    comodos = db.query(ImovelComodo).filter(ImovelComodo.imovel_id == im.id).all()
    itens_cat = db.query(ItemVistoria).limit(4).all()

    db.add(Endereco(imovel_id=im.id, **endereco))

    ct = Contrato(
        imovel_id=im.id,
        locatario_id=locatario_id,
        data_inicio=hoje,
        data_fim=hoje + timedelta(days=dias_contrato),
        valor_mensal=valor,
        status="ativo",
    )
    db.add(ct)
    db.flush()
    im.status = status_final if status_final != "disponivel" else "locado"

    for tipo_ag in ("inicial", "encerramento"):
        db.add(
            AgendamentoVistoria(
                contrato_id=ct.id,
                tipo=tipo_ag,
                data_agendada=hoje if tipo_ag == "inicial" else hoje + timedelta(days=dias_contrato),
                observacao=f"Vistoria {tipo_ag} — {titulo}",
            )
        )

    ck = Checklist(
        contrato_id=ct.id,
        vistoriador_id=vistoriador_id,
        tipo=checklist_tipo,
        status=checklist_status,
        data_vistoria=hoje,
    )
    db.add(ck)
    db.flush()

    if preencher_itens and comodos and itens_cat:
        estados = ["otimo", "bom", "regular", "ruim"]
        for i, comodo in enumerate(comodos[:3]):
            for j, cat in enumerate(itens_cat[:2]):
                db.add(
                    ChecklistItem(
                        checklist_id=ck.id,
                        comodo_id=comodo.id,
                        item_vistoria_id=cat.id,
                        estado=estados[(i + j) % len(estados)],
                        observacao=f"Verificado em {comodo.nome}",
                    )
                )

    for pb in problemas or []:
        db.add(Problema(contrato_id=ct.id, **pb))

    return {"imovel_id": im.id, "contrato_id": ct.id, "checklist_id": ck.id}


def _clear_data_keep_users(db: Session) -> None:
    db.query(ChecklistItemFoto).delete()
    db.query(ChecklistItem).delete()
    db.query(Checklist).delete()
    db.query(AgendamentoVistoria).delete()
    db.query(Problema).delete()
    db.query(Contrato).delete()
    db.query(Endereco).delete()
    db.query(ImovelComodo).delete()
    db.query(Imovel).delete()
    db.query(ItemVistoria).delete()
    db.query(LogOperacao).delete()
    db.query(RefreshToken).delete()
    db.commit()


def _populate_sample_data(
    db: Session,
    *,
    admin: Usuario,
    gestor: Usuario | None,
    vist1: Usuario,
    vist2: Usuario | None,
    loc1: Usuario,
    loc2: Usuario | None,
    loc3: Usuario | None,
) -> dict:
    catalog = [
        ("Piso", "estrutura"), ("Paredes", "estrutura"), ("Teto", "estrutura"),
        ("Portas", "acabamento"), ("Janelas", "acabamento"), ("Tomadas", "eletrica"),
        ("Iluminação", "eletrica"), ("Pintura", "acabamento"),
        ("Torneiras", "hidraulica"), ("Box", "banheiro"),
    ]
    for nome, cat in catalog:
        db.add(ItemVistoria(nome=nome, categoria=cat))
    db.flush()

    created = []
    vist_b = vist2 or vist1
    loc_b = loc2 or loc1
    loc_c = loc3 or loc1

    created.append(_create_imovel_com_contrato(
        db, codigo="IM-001", titulo="Apartamento Centro", tipo="Apartamento", tamanho="65m²",
        status_final="locado", locatario_id=loc1.id, vistoriador_id=vist1.id, valor=2500,
        endereco={"rua": "Rua das Flores", "numero": "100", "bairro": "Centro", "cidade": "São Paulo", "estado": "SP", "cep": "01001000", "latitude": -23.5505, "longitude": -46.6333},
        checklist_status="em_preenchimento", preencher_itens=True,
        problemas=[{"titulo": "Torneira pingando", "descricao": "Cozinha", "prioridade": "normal", "status": "aberto"}],
    ))

    created.append(_create_imovel_com_contrato(
        db, codigo="IM-002", titulo="Casa Jardim América", tipo="Casa", tamanho="120m²",
        status_final="locado", locatario_id=loc_b.id, vistoriador_id=vist_b.id, valor=4200,
        offset_dias=-30,
        endereco={"rua": "Av. Paulista", "numero": "1500", "bairro": "Bela Vista", "cidade": "São Paulo", "estado": "SP", "cep": "01310100", "latitude": -23.5614, "longitude": -46.6559},
        checklist_status="pendente_aceite", preencher_itens=True,
        problemas=[
            {"titulo": "Infiltração no teto", "prioridade": "urgente", "status": "aberto"},
            {"titulo": "Porta emperrada", "prioridade": "alta", "status": "aberto"},
        ],
    ))

    created.append(_create_imovel_com_contrato(
        db, codigo="IM-003", titulo="Studio Moema", tipo="Studio", tamanho="35m²",
        status_final="locado", locatario_id=loc_c.id, vistoriador_id=vist1.id, valor=1800,
        offset_dias=-60,
        endereco={"rua": "Rua Gaivota", "numero": "200", "bairro": "Moema", "cidade": "São Paulo", "estado": "SP", "cep": "04522000", "latitude": -23.6012, "longitude": -46.6643},
        checklist_status="aceito", preencher_itens=True,
    ))

    for codigo, titulo, tipo, tam in [
        ("IM-004", "Cobertura Vila Mariana", "Cobertura", "180m²"),
        ("IM-005", "Kitnet Consolação", "Kitnet", "28m²"),
    ]:
        im = Imovel(codigo=codigo, titulo=titulo, tipo=tipo, tamanho=tam, garagem=False, status="disponivel")
        db.add(im)
        db.flush()
        ensure_default_comodos(db, im.id)
        db.add(Endereco(
            imovel_id=im.id, rua=f"Rua {codigo}", numero="50",
            bairro="Vila Mariana", cidade="São Paulo", estado="SP", cep="04101000",
            latitude=-23.5890 + (0.01 * int(codigo[-1])),
            longitude=-46.6340 - (0.01 * int(codigo[-1])),
        ))

    im6 = Imovel(codigo="IM-006", titulo="Sala Comercial Pinheiros", tipo="Comercial", tamanho="90m²", status="em_vistoria")
    db.add(im6)
    db.flush()
    ensure_default_comodos(db, im6.id)
    db.add(Endereco(
        imovel_id=im6.id, rua="Rua dos Pinheiros", numero="800",
        bairro="Pinheiros", cidade="São Paulo", estado="SP", cep="05422000",
        latitude=-23.5675, longitude=-46.7033,
    ))

    log_operacao(db, admin.id, "seed", "sistema", None, "Dados de exemplo recriados")
    db.commit()

    return {
        "seeded": True,
        "message": "Dados recriados (usuários preservados)",
        "totals": {
            "usuarios": db.query(Usuario).count(),
            "imoveis": db.query(Imovel).count(),
            "contratos": db.query(Contrato).count(),
            "checklists": db.query(Checklist).count(),
            "problemas": db.query(Problema).count(),
            "itens_vistoria": db.query(ItemVistoria).count(),
        },
        "registros": created,
    }


def run_refresh_data(db: Session) -> dict:
    """Apaga imóveis, contratos, vistorias e problemas; mantém usuários."""
    admin = db.query(Usuario).filter(Usuario.email == "admin@onecheck.local").first()
    vist1 = db.query(Usuario).filter(Usuario.email == "vistoriador@onecheck.local").first()
    loc1 = db.query(Usuario).filter(Usuario.email == "locatario@onecheck.local").first()
    if not admin or not vist1 or not loc1:
        return {
            "seeded": False,
            "message": "Usuários mínimos ausentes (admin, vistoriador ou locatario).",
        }

    gestor = db.query(Usuario).filter(Usuario.email == "gestor@onecheck.local").first()
    vist2 = db.query(Usuario).filter(Usuario.email == "ana.vistoriadora@onecheck.local").first()
    loc2 = db.query(Usuario).filter(Usuario.email == "pedro.locatario@onecheck.local").first()
    loc3 = db.query(Usuario).filter(Usuario.email == "julia.locatario@onecheck.local").first()

    _clear_data_keep_users(db)
    return _populate_sample_data(
        db,
        admin=admin,
        gestor=gestor,
        vist1=vist1,
        vist2=vist2,
        loc1=loc1,
        loc2=loc2,
        loc3=loc3,
    )


def run_seed(db: Session, force: bool = False) -> dict:
    if db.query(Usuario).count() > 0 and not force:
        return {
            "seeded": False,
            "message": "Banco já possui dados. Use force=true, mode=expand ou mode=refresh_data.",
            "usuarios": db.query(Usuario).count(),
        }

    if force:
        _clear_all(db)

    admin = Usuario(
        nome="Administrador",
        email="admin@onecheck.local",
        senha_hash=hash_password("admin123"),
        role="admin",
        mfa_enabled=True,
        mfa_secret=MFA_SECRET,
    )
    gestor = Usuario(
        nome="Carlos Gestor",
        email="gestor@onecheck.local",
        senha_hash=hash_password("gestor123"),
        role="gestor",
        mfa_enabled=True,
        mfa_secret=MFA_SECRET,
    )
    vist1 = Usuario(
        nome="João Vistoriador",
        email="vistoriador@onecheck.local",
        senha_hash=hash_password("vistor123"),
        role="vistoriador",
        mfa_enabled=True,
        mfa_secret=MFA_SECRET,
    )
    vist2 = Usuario(
        nome="Ana Vistoriadora",
        email="ana.vistoriadora@onecheck.local",
        senha_hash=hash_password("vistor123"),
        role="vistoriador",
        mfa_enabled=True,
        mfa_secret=MFA_SECRET,
    )
    loc1 = Usuario(
        nome="Maria Locatária",
        email="locatario@onecheck.local",
        senha_hash=hash_password("locat123"),
        role="locatario",
    )
    loc2 = Usuario(
        nome="Pedro Locatário",
        email="pedro.locatario@onecheck.local",
        senha_hash=hash_password("locat123"),
        role="locatario",
    )
    loc3 = Usuario(
        nome="Julia Locatária",
        email="julia.locatario@onecheck.local",
        senha_hash=hash_password("locat123"),
        role="locatario",
    )
    db.add_all([admin, gestor, vist1, vist2, loc1, loc2, loc3])
    db.flush()

    result = _populate_sample_data(
        db,
        admin=admin,
        gestor=gestor,
        vist1=vist1,
        vist2=vist2,
        loc1=loc1,
        loc2=loc2,
        loc3=loc3,
    )

    totp = pyotp.TOTP(MFA_SECRET)
    return {
        **result,
        "message": "Banco populado com dados completos",
        "usuarios": [
            {"email": "admin@onecheck.local", "senha": "admin123", "mfa": True},
            {"email": "gestor@onecheck.local", "senha": "gestor123", "mfa": True},
            {"email": "vistoriador@onecheck.local", "senha": "vistor123", "mfa": True},
            {"email": "ana.vistoriadora@onecheck.local", "senha": "vistor123", "mfa": True},
            {"email": "locatario@onecheck.local", "senha": "locat123", "mfa": False},
            {"email": "pedro.locatario@onecheck.local", "senha": "locat123", "mfa": False},
            {"email": "julia.locatario@onecheck.local", "senha": "locat123", "mfa": False},
        ],
        "mfa_secret": MFA_SECRET,
        "mfa_codigo_atual": totp.now(),
    }


def run_expand(db: Session) -> dict:
    """Adiciona dados extras sem apagar existentes."""
    if db.query(Usuario).filter(Usuario.email == "ana.vistoriadora@onecheck.local").first():
        return {"seeded": False, "message": "Dados expandidos já existem (ana.vistoriadora@onecheck.local)."}

    vist2 = Usuario(
        nome="Ana Vistoriadora",
        email="ana.vistoriadora@onecheck.local",
        senha_hash=hash_password("vistor123"),
        role="vistoriador",
        mfa_enabled=True,
        mfa_secret=MFA_SECRET,
    )
    loc2 = db.query(Usuario).filter(Usuario.email == "pedro.locatario@onecheck.local").first()
    loc3 = db.query(Usuario).filter(Usuario.email == "julia.locatario@onecheck.local").first()
    vist1 = db.query(Usuario).filter(Usuario.email == "vistoriador@onecheck.local").first()

    if not loc2:
        loc2 = Usuario(nome="Pedro Locatário", email="pedro.locatario@onecheck.local", senha_hash=hash_password("locat123"), role="locatario")
        db.add(loc2)
    if not loc3:
        loc3 = Usuario(nome="Julia Locatária", email="julia.locatario@onecheck.local", senha_hash=hash_password("locat123"), role="locatario")
        db.add(loc3)
    db.add(vist2)
    db.flush()

    for nome, cat in [("Torneiras", "hidraulica"), ("Box", "banheiro")]:
        if not db.query(ItemVistoria).filter(ItemVistoria.nome == nome).first():
            db.add(ItemVistoria(nome=nome, categoria=cat))
    db.flush()

    created = []
    if loc2 and vist1:
        created.append(_create_imovel_com_contrato(
            db, codigo="IM-002", titulo="Casa Jardim América", tipo="Casa", tamanho="120m²",
            status_final="locado", locatario_id=loc2.id, vistoriador_id=vist2.id, valor=4200,
            offset_dias=-30,
            endereco={"rua": "Av. Paulista", "numero": "1500", "bairro": "Bela Vista", "cidade": "São Paulo", "estado": "SP", "cep": "01310100", "latitude": -23.5614, "longitude": -46.6559},
            checklist_status="pendente_aceite", preencher_itens=True,
            problemas=[{"titulo": "Infiltração no teto", "prioridade": "urgente", "status": "aberto"}],
        ))

    if not db.query(Imovel).filter(Imovel.codigo == "IM-004").first():
        im = Imovel(codigo="IM-004", titulo="Cobertura Vila Mariana", tipo="Cobertura", tamanho="180m²", status="disponivel")
        db.add(im)
        db.flush()
        ensure_default_comodos(db, im.id)

    db.commit()
    return {
        "seeded": True,
        "message": "Dados expandidos adicionados",
        "registros": created,
        "totals": {
            "usuarios": db.query(Usuario).count(),
            "imoveis": db.query(Imovel).count(),
            "contratos": db.query(Contrato).count(),
            "checklists": db.query(Checklist).count(),
            "problemas": db.query(Problema).count(),
        },
    }
