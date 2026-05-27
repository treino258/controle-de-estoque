"""Modelo de produtos.

Product guarda dados permanentes do item — o cadastro base.
Não guarda estoque atual: isso é calculado dinamicamente
somando as movimentações em StockMovement.

Por que não salvar estoque diretamente?
- Evita inconsistência entre o número salvo e as movimentações reais
- Permite auditoria completa: qualquer número pode ser explicado por eventos
- Prepara a base para ML: features ricas de histórico por produto
"""

from sqlalchemy import Boolean, Column, Float, Integer, String
from sqlalchemy.orm import relationship

from app.database.connection import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False, unique=True, index=True)
    categoria = Column(String, nullable=False)
    unidade_medida = Column(String, nullable=False)
    estoque_minimo = Column(Float, nullable=False, default=0)

    # Controle de abertura: alguns produtos precisam rastrear quando são abertos
    # Ex: leite, creme de leite — têm validade diferente após abertos
    controla_abertura = Column(Boolean, default=False)
    validade_apos_abertura = Column(Integer, nullable=True)  # dias

    # Relacionamento com movimentações (substitui purchases + opened_products)
    movements = relationship(
        "StockMovement",
        back_populates="product",
        cascade="all, delete",
        foreign_keys="StockMovement.product_id",
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} nome={self.nome!r}>"