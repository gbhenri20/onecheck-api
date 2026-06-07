from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import SEED_SECRET
from app.database import get_db
from app.schemas import fail, ok
from app.seed_service import run_expand, run_refresh_data, run_seed

router = APIRouter(prefix="/admin", tags=["admin"])


class SeedRequest(BaseModel):
    force: bool = False
    mode: str = "full"  # full | expand | refresh_data


@router.post("/seed")
def seed_database(
    body: SeedRequest | None = None,
    x_seed_secret: str | None = Header(default=None, alias="X-Seed-Secret"),
    db: Session = Depends(get_db),
):
    if not SEED_SECRET or x_seed_secret != SEED_SECRET:
        raise HTTPException(status_code=403, detail="Seed secret inválido")

    body = body or SeedRequest()
    if body.mode == "expand":
        result = run_expand(db)
    elif body.mode == "refresh_data":
        result = run_refresh_data(db)
    else:
        result = run_seed(db, force=body.force)

    if not result.get("seeded"):
        return fail(result["message"])

    return ok(result)
