"""Criação das tabelas do projeto."""

from app.database.connection import engine
import app.models  
from app.models.opened_product import OpenedProduct
from app.database.connection import Base, engine

def init_db() -> None:
    """Cria as tabelas caso ainda não existam."""
    Base.metadata.create_all(bind=engine)
