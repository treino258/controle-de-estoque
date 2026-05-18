"""Configuração de conexão com o banco de dados SQLite.

Este módulo concentra tudo que é necessário para o SQLAlchemy
conversar com o banco. Ao separar esta parte, evitamos repetir
configuração em vários lugares da aplicação.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///cafeteria_estoque.db"

# Engine é o objeto que sabe "como" conectar ao banco.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # necessário para Streamlit + SQLite
)

# SessionLocal cria sessões de banco quando precisamos ler/escrever dados.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
