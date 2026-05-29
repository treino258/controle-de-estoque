"""Ledger imutável de movimentações de estoque."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.mixins import TenantMixin, TimestampMixin

TIPOS_ENTRADA = {"entrada", "estorno"}
TIPOS_SAIDA = {"abertura", "consumo", "perda"}
TIPOS_COM_DIRECAO = {"ajuste"}


class StockMovement(TenantMixin, TimestampMixin, Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Lote em uso (consumo, perda de aberto)
    lot_id = Column(
        Integer,
        ForeignKey(
            "stock_lots.id",
            ondelete="RESTRICT",
            use_alter=True,
            name="fk_movement_lot",
        ),
        nullable=True,
        index=True,
    )

    tipo = Column(
        Enum(
            "entrada",
            "abertura",
            "consumo",
            "perda",
            "ajuste",
            "estorno",
            name="movement_type",
        ),
        nullable=False,
    )

    quantidade = Column(Float, nullable=False)

    direcao = Column(
        Enum("entrada", "saida", name="movement_direction"),
        nullable=True,
    )

    # Perda: de qual estoque saiu
    estoque_afetado = Column(
        Enum("fechado", "aberto", name="estoque_afetado"),
        nullable=True,
    )

    preco_unitario = Column(Numeric(12, 2), nullable=True)
    preco_total = Column(Numeric(12, 2), nullable=True)
    fornecedor = Column(String, nullable=True)
    tempo_entrega = Column(Integer, nullable=True)
    data_validade = Column(Date, nullable=True)

    validade_aberto = Column(Date, nullable=True)

    # Referência: abertura←entrada, estorno←movimento, ajuste←origem
    movimento_referencia_id = Column(
        Integer,
        ForeignKey("stock_movements.id"),
        nullable=True,
        index=True,
    )

    motivo = Column(String, nullable=True)

    data_movimento = Column(Date, nullable=False)
    observacao = Column(String, nullable=True)

    product = relationship("Product", back_populates="movements")
    lot = relationship(
        "StockLot",
        foreign_keys=[lot_id],
        back_populates="movements",
    )
    movimento_referencia = relationship(
        "StockMovement",
        remote_side=[id],
        foreign_keys=[movimento_referencia_id],
        backref="movimentos_derivados",
    )

    __table_args__ = (
        CheckConstraint("quantidade > 0", name="quantidade_positiva"),
        CheckConstraint(
            "(tipo = 'ajuste' AND direcao IS NOT NULL) "
            "OR (tipo != 'ajuste' AND direcao IS NULL)",
            name="ajuste_precisa_direcao",
        ),
        CheckConstraint(
            "(tipo NOT IN ('perda', 'ajuste')) "
            "OR (motivo IS NOT NULL AND length(trim(motivo)) > 0)",
            name="perda_ajuste_precisa_motivo",
        ),
        CheckConstraint(
            "(tipo != 'perda') OR (estoque_afetado IS NOT NULL)",
            name="perda_precisa_estoque_afetado",
        ),
        Index("ix_movements_product_date", "product_id", "data_movimento"),
        Index("ix_movements_tipo", "tipo"),
        Index("ix_movements_validade_aberto", "validade_aberto"),
    )

    def get_sinal(self) -> int:
        if self.tipo in TIPOS_ENTRADA:
            return +1
        if self.tipo in TIPOS_SAIDA:
            return -1
        if self.tipo == "ajuste":
            return +1 if self.direcao == "entrada" else -1
        raise ValueError(f"Tipo desconhecido: {self.tipo}")

    def get_quantidade_efetiva(self) -> float:
        return self.quantidade * self.get_sinal()

    def __repr__(self) -> str:
        sinal = "+" if self.get_sinal() > 0 else "-"
        return (
            f"<StockMovement id={self.id} product_id={self.product_id} "
            f"tipo={self.tipo} qty={sinal}{self.quantidade}>"
        )
