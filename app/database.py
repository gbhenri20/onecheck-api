from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

_connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args=_connect_args,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema_updates() -> None:
    """Cria tabelas e adiciona colunas novas em bancos já existentes."""
    Base.metadata.create_all(bind=engine)
    insp = inspect(engine)
    if "enderecos" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("enderecos")}
    with engine.begin() as conn:
        if "latitude" not in cols:
            conn.execute(text("ALTER TABLE enderecos ADD COLUMN latitude FLOAT"))
        if "longitude" not in cols:
            conn.execute(text("ALTER TABLE enderecos ADD COLUMN longitude FLOAT"))
