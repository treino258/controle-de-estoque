"""Modelo de compras (eventos de entrada em estoque).

Não salvamos estoque atual aqui. Cada compra é uma movimentação.
Depois, o estoque atual é calculado somando movimentações.

Vantagem: evita inconsistência e preserva histórico completo.
"""

from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    produto_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantidade = Column(Float, nullable=False)
    preco_unitario = Column(Float, nullable=False)
    preco_total = Column(Float, nullable=False)
    data_compra = Column(Date, nullable=False)
    data_validade = Column(Date, nullable=True)
    fornecedor = Column(String, nullable=True)
    tempo_entrega = Column(Integer, nullable=True)  # dias

    product = relationship("Product", back_populates="purchases")
