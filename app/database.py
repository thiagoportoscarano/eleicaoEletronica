from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

_url = settings.database_url
_kwargs: dict = {}
if _url.startswith("sqlite"):
    _kwargs["connect_args"] = {"check_same_thread": False}
    if _url in ("sqlite://", "sqlite:///:memory:"):
        _kwargs["poolclass"] = StaticPool  # mesma conexão => banco em memória compartilhado (testes)

engine = create_engine(_url, **_kwargs)

if _url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _ativar_fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
