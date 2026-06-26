from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.database.seed import DEFAULT_TENANT_ID
from app.models import Expense, Sale


def list_sales(session: Session) -> list[Sale]:
    return session.query(Sale).all()


def list_expenses(session: Session) -> list[Expense]:
    return session.query(Expense).all()


def list_active_expenses(session: Session) -> list[Expense]:
    return (
        session.query(Expense)
        .filter(Expense.is_deleted.is_(False))
        .order_by(Expense.data.desc())
        .all()
    )


def get_expense(session: Session, expense_id: int) -> Expense | None:
    return session.query(Expense).filter(Expense.id == expense_id).first()


def create_expense(
    session: Session, nome: str, categoria: str, valor: float, data_gasto
):
    expense = Expense(
        tenant_id=DEFAULT_TENANT_ID,
        nome=nome,
        categoria=categoria,
        valor=valor,
        data=data_gasto,
    )
    session.add(expense)
    return expense


def soft_delete_expense(session: Session, expense: Expense) -> None:
    expense.is_deleted = True
    expense.deleted_at = datetime.utcnow()
