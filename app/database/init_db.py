"""Criação das tabelas e seed inicial."""

from app.database.connection import Base, engine
from app.database.connection import SessionLocal
from app.database.seed import ensure_default_tenant

# Importa models para registrar metadata
import app.models  # noqa: F401


def init_db() -> None:
    """Cria tabelas e garante tenant padrão."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        ensure_default_tenant(session)
