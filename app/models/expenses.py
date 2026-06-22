"""Despesas operacionais."""

from sqlalchemy import Column, Date, DateTime, Enum, Integer, Numeric, String, Boolean

from app.database.connection import Base
from app.models.mixins import TenantMixin, TimestampMixin


class Expense(TenantMixin, TimestampMixin, Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True)

    nome = Column(String, nullable=False)
    categoria = Column(
        Enum("fixo", "variavel", name="expense_category"),
        nullable=False,
    )
    valor = Column(Numeric(12, 2), nullable=False)
    data = Column(Date, nullable=False)
    
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)