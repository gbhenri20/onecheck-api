from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.config import UPLOAD_DIR
from app.schemas import ok

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return ok({"status": "ok", "service": "onecheck-api"})


@router.get("/uploads/{filename}")
def serve_upload(filename: str):
    path = UPLOAD_DIR / filename
    if not path.exists() or not path.is_file():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(path)
