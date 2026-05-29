"""Vendas registradas no dashboard financeiro."""

from sqlalchemy import Column, Date, Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.mixins import TenantMixin, TimestampMixin


class Sale(TenantMixin, TimestampMixin, Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Snapshot para histórico se produto for renomeado/desativado
    produto_nome = Column(String, nullable=True)

    quantidade = Column(Float, nullable=False)
    valor_unitario = Column(Numeric(12, 2), nullable=False)
    valor_total = Column(Numeric(12, 2), nullable=False)
    data_venda = Column(Date, nullable=False)

    product = relationship("Product", back_populates="sales")
