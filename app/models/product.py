"""Modelo de produtos.

Product guarda dados permanentes do item:
- nome, categoria, unidade e estoque mínimo.

Separar Product de Purchase é importante porque:
1) Product representa o cadastro base do item.
2) Purchase representa eventos que acontecem ao longo do tempo.

Essa separação mantém o histórico e deixa o sistema pronto para
analytics e machine learning no futuro.
"""

from sqlalchemy import Column, Float, Integer, String, Boolean
from sqlalchemy.orm import relationship

from app.database.connection import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False, unique=True, index=True)
    categoria = Column(String, nullable=False)
    unidade_medida = Column(String, nullable=False)
    estoque_minimo = Column(Float, nullable=False, default=0)
    

    purchases = relationship("Purchase", back_populates="product", cascade="all,delete")

    controla_abertura = Column(Boolean,default=False,)

    validade_apos_abertura = Column(Integer,nullable=True,)