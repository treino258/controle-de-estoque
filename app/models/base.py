"""Base dos modelos SQLAlchemy.

SQLAlchemy é uma biblioteca Python para acessar banco de dados.
ORM (Object-Relational Mapping) é a técnica de mapear tabelas
(relacional) para classes Python (objetos).

Com isso, em vez de escrever SQL manual o tempo todo,
conseguimos trabalhar de forma mais didática e orientada a objetos.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()
