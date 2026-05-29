"""Lote em uso após abertura de produto.

Cada abertura gera um lote com saldo próprio (FEFO, validade, consumo).
O ledger em stock_movements continua auditável; o lote é estado operacional.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.mixins import TenantMixin, TimestampMixin


class StockLot(TenantMixin, TimestampMixin, Base):
    __tablename__ = "stock_lots"

    id = Column(Integer, primary_key=True, index=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Movimentação de abertura que originou este lote
    abertura_movement_id = Column(
        Integer,
        ForeignKey("stock_movements.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )

    quantidade_inicial = Column(Float, nullable=False)
    quantidade_atual = Column(Float, nullable=False)

    data_abertura = Column(Date, nullable=False)
    validade = Column(Date, nullable=True)

    status = Column(
        Enum("open", "closed", name="lot_status"),
        nullable=False,
        default="open",
    )

    product = relationship("Product", back_populates="lots")
    abertura_movement = relationship(
        "StockMovement",
        foreign_keys=[abertura_movement_id],
    )
    movements = relationship(
        "StockMovement",
        foreign_keys="StockMovement.lot_id",
        back_populates="lot",
    )

    __table_args__ = (
        CheckConstraint("quantidade_inicial > 0", name="lot_qty_inicial_positiva"),
        CheckConstraint("quantidade_atual >= 0", name="lot_qty_atual_nao_negativa"),
        Index("ix_lots_product_status", "product_id", "status"),
        Index("ix_lots_validade", "validade"),
    )

    def __repr__(self) -> str:
        return (
            f"<StockLot id={self.id} product_id={self.product_id} "
            f"qty={self.quantidade_atual}/{self.quantidade_inicial} "
            f"status={self.status}>"
        )
