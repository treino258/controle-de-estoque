from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import StockMovement


def list_recent_corrections(session: Session, limit: int = 10) -> list[StockMovement]:
    return (
        session.query(StockMovement)
        .filter(StockMovement.tipo == "ajuste")
        .filter(StockMovement.movimento_referencia_id.isnot(None))
        .order_by(StockMovement.data_movimento.desc())
        .limit(limit)
        .all()
    )
