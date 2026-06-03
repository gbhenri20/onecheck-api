"""Popula banco com usuários, catálogo e dados de exemplo."""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pyotp
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.models import (
    AgendamentoVistoria,
    Checklist,
    Contrato,
    Endereco,
    Imovel,
    ImovelComodo,
    ItemVistoria,
    Usuario,
)
from app.serializers import ensure_default_comodos

MFA_SECRET = "JBSWY3DPEHPK3PXP"  # Use Google Authenticator com este secret para admin/vistoriador


def seed(db: Session) -> None:
    if db.query(Usuario).count() > 0:
        print("Banco já possui dados. Seed ignorado.")
        return

    admin = Usuario(
        nome="Administrador",
        email="admin@onecheck.local",
        senha_hash=hash_password("admin123"),
        role="admin",
        mfa_enabled=True,
        mfa_secret=MFA_SECRET,
    )
    vistoriador = Usuario(
        nome="João Vistoriador",
        email="vistoriador@onecheck.local",
        senha_hash=hash_password("vistor123"),
        role="vistoriador",
        mfa_enabled=True,
        mfa_secret=MFA_SECRET,
    )
    locatario = Usuario(
        nome="Maria Locatária",
        email="locatario@onecheck.local",
        senha_hash=hash_password("locat123"),
        role="locatario",
        mfa_enabled=False,
    )
    db.add_all([admin, vistoriador, locatario])
    db.flush()

    catalog = [
        "Piso", "Paredes", "Teto", "Portas",
        "Janelas", "Tomadas", "Iluminação", "Pintura",
    ]
    for nome in catalog:
        db.add(ItemVistoria(nome=nome, categoria="geral"))
    db.flush()

    imovel = Imovel(
        codigo="IM-001",
        titulo="Apartamento Centro",
        tipo="Apartamento",
        tamanho="65m²",
        garagem=True,
        garagem_vagas=1,
        status="disponivel",
    )
    db.add(imovel)
    db.flush()
    ensure_default_comodos(db, imovel.id)

    db.add(
        Endereco(
            imovel_id=imovel.id,
            rua="Rua das Flores",
            numero="100",
            bairro="Centro",
            cidade="São Paulo",
            estado="SP",
            cep="01001000",
        )
    )

    imovel.status = "locado"
    hoje = date.today()
    contrato = Contrato(
        imovel_id=imovel.id,
        locatario_id=locatario.id,
        data_inicio=hoje,
        data_fim=hoje + timedelta(days=365),
        valor_mensal=2500.00,
        status="ativo",
    )
    db.add(contrato)
    db.flush()

    for tipo in ("inicial", "encerramento"):
        db.add(
            AgendamentoVistoria(
                contrato_id=contrato.id,
                tipo=tipo,
                data_agendada=hoje if tipo == "inicial" else hoje + timedelta(days=365),
            )
        )

    checklist = Checklist(
        contrato_id=contrato.id,
        vistoriador_id=vistoriador.id,
        tipo="inicial",
        status="em_preenchimento",
        data_vistoria=hoje,
    )
    db.add(checklist)
    db.commit()

    totp = pyotp.TOTP(MFA_SECRET)
    print("Seed concluído!")
    print("")
    print("Usuários:")
    print("  admin@onecheck.local / admin123 (MFA)")
    print("  vistoriador@onecheck.local / vistor123 (MFA)")
    print("  locatario@onecheck.local / locat123 (sem MFA)")
    print("")
    print(f"MFA secret (admin/vistoriador): {MFA_SECRET}")
    print(f"MFA código atual: {totp.now()}")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed(session)
