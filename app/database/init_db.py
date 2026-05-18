"""Criação das tabelas do projeto."""

from app.database.connection import engine
from app.models import Base


def init_db() -> None:
    """Cria as tabelas caso ainda não existam."""
    Base.metadata.create_all(bind=engine)
