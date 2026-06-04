from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import CORS_ORIGINS, UPLOAD_DIR
from app.database import Base, engine
from app.routers import auth_router, checklists, contratos, dashboard, health, imoveis, usuarios


@asynccontextmanager
async def lifespan(app: FastAPI):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="OneCheck API",
    version="1.0.0",
    description="API REST para integração Web + Mobile OneCheck",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = "/api/v1"

app.include_router(health.router, prefix=prefix)
app.include_router(auth_router.router, prefix=prefix)
app.include_router(usuarios.router, prefix=prefix)
app.include_router(imoveis.router, prefix=prefix)
app.include_router(contratos.router, prefix=prefix)
app.include_router(checklists.router, prefix=prefix)
app.include_router(dashboard.router, prefix=prefix)


@app.get("/")
def root():
    return {"service": "OneCheck API", "docs": "/docs", "health": f"{prefix}/health"}
