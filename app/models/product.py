"""Modelo de produtos."""

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.mixins import TenantMixin, TimestampMixin


class Product(TenantMixin, TimestampMixin, Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False, index=True)
    categoria = Column(String, nullable=False)
    unidade_medida = Column(String, nullable=False)
    estoque_minimo = Column(Float, nullable=False, default=0)
    ativo = Column(Boolean, default=True, nullable=False)

    controla_abertura = Column(Boolean, default=False)
    validade_apos_abertura = Column(Integer, nullable=True)

    movements = relationship(
        "StockMovement",
        back_populates="product",
        foreign_keys="StockMovement.product_id",
    )
    lots = relationship(
        "StockLot",
        back_populates="product",
        foreign_keys="StockLot.product_id",
    )
    sales = relationship("Sale", back_populates="product")

    __table_args__ = (
        UniqueConstraint("tenant_id", "nome", name="uq_product_tenant_nome"),
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} nome={self.nome!r}>"
