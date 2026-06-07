from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import SEED_SECRET
from app.data_status import get_data_status
from app.database import get_db
from app.schemas import fail, ok
from app.seed_service import run_expand, run_refresh_data, run_seed

router = APIRouter(prefix="/admin", tags=["admin"])


class SeedRequest(BaseModel):
    force: bool = False
    mode: str = Field(default="full", description="full | expand | refresh_data")


def _require_seed_secret(x_seed_secret: str | None) -> None:
    if not SEED_SECRET or x_seed_secret != SEED_SECRET:
        raise HTTPException(status_code=403, detail="Seed secret inválido")


def _refresh_data(db: Session) -> dict:
    result = run_refresh_data(db)
    if not result.get("seeded"):
        return fail(result["message"])
    result["preservado"] = "usuarios"
    return ok(result)


@router.get("/data/status")
def data_status(
    x_seed_secret: str | None = Header(default=None, alias="X-Seed-Secret"),
    db: Session = Depends(get_db),
):
    """Retorna totais do banco sem alterar dados."""
    _require_seed_secret(x_seed_secret)
    return ok(get_data_status(db))


@router.post("/refresh-data")
@router.put("/refresh-data")
@router.patch("/refresh-data")
def refresh_data(
    x_seed_secret: str | None = Header(default=None, alias="X-Seed-Secret"),
    db: Session = Depends(get_db),
):
    """
    Recria imóveis (com lat/lng), contratos, vistorias, problemas e catálogo.
    **Não altera usuários** (senhas, MFA e perfis permanecem).
    """
    _require_seed_secret(x_seed_secret)
    return _refresh_data(db)


@router.post("/seed")
def seed_database(
    body: SeedRequest | None = None,
    x_seed_secret: str | None = Header(default=None, alias="X-Seed-Secret"),
    db: Session = Depends(get_db),
):
    _require_seed_secret(x_seed_secret)

    body = body or SeedRequest()
    if body.mode == "expand":
        result = run_expand(db)
    elif body.mode == "refresh_data":
        result = run_refresh_data(db)
    else:
        result = run_seed(db, force=body.force)

    if not result.get("seeded"):
        return fail(result["message"])

    if body.mode == "refresh_data":
        result["preservado"] = "usuarios"
    return ok(result)
