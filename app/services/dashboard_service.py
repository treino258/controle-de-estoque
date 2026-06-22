from __future__ import annotations

from datetime import date, timedelta

from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database.seed import DEFAULT_TENANT_ID
from app.models import Expense, Product, Sale, StockLot, StockMovement
from app.models.enums import ProductType

from app.utils import _to_float

from app.services import get_estoque_aberto, get_estoque_fechado, get_estoque_total, get_lotes_abertos




def get_dashboard_estoque(session: Session) -> list[dict]:
    produtos = (
    session.query(Product)
    .filter(
        Product.ativo.is_(True),
        Product.tipo_produto.in_(
            [
                ProductType.MATERIA_PRIMA,
                ProductType.CONSUMIVEL,
                ProductType.PRODUTO_FINAL,
            ]
        ),
    )
    .all()
)
    resultado = []

    for p in produtos:
        fechado = get_estoque_fechado(session, p.id)
        aberto = get_estoque_aberto(session, p.id) if p.controla_abertura else 0.0
        total = fechado + aberto

        resultado.append({
            "id": p.id,
            "nome": p.nome,
            "tipo": p.tipo_produto.value,
            "unidade_medida": p.unidade_medida,
            "estoque_minimo": p.estoque_minimo,
            "estoque_fechado": fechado,
            "estoque_aberto": aberto,
            "estoque_total": total,
            "abaixo_minimo": total < p.estoque_minimo,
            "controla_abertura": p.controla_abertura,
        })

    return resultado


def get_produtos_abaixo_minimo(session: Session) -> list[dict]:
    return [p for p in get_dashboard_estoque(session) if p["abaixo_minimo"]]


def get_abertos_proximos_vencimento(session: Session, dias: int = 3) -> list[dict]:
    """Lotes abertos com validade nos próximos N dias."""
    hoje = date.today()
    limite = hoje + timedelta(days=dias)

    lotes = (
        session.query(StockLot)
        .filter(StockLot.status == "open")
        .filter(StockLot.quantidade_atual > 1e-9)
        .filter(StockLot.validade.isnot(None))
        .filter(StockLot.validade <= limite)
        .filter(StockLot.validade >= hoje)
        .order_by(StockLot.validade.asc())
        .all()
    )

    return [
        {
            "lot_id": lot.id,
            "produto": lot.product.nome,
            "quantidade": lot.quantidade_atual,
            "validade": lot.validade,
            "dias_restantes": (lot.validade - hoje).days,
        }
        for lot in lotes
    ]


def get_lotes_abertos_detalhados(session: Session) -> list[dict]:
    """Lista lotes abertos para exibição na UI."""
    lotes = get_lotes_abertos(session)
    return [
        {
            "lot_id": lot.id,
            "product_id": lot.product_id,
            "produto": lot.product.nome,
            "quantidade_atual": lot.quantidade_atual,
            "validade": lot.validade,
            "data_abertura": lot.data_abertura,
            "dias_restantes": (
                (lot.validade - date.today()).days if lot.validade else None
            ),
        }
        for lot in lotes
    ]



def get_historico_produto(
    session: Session,
    product_id: int,
    limit: int = 50,
) -> list[dict]:
    movs = (
        session.query(StockMovement)
        .filter(StockMovement.product_id == product_id)
        .order_by(
            StockMovement.data_movimento.desc(),
            StockMovement.id.desc(),
        )
        .limit(limit)
        .all()
    )

    return [
        {
            "id": m.id,
            "data": m.data_movimento,
            "tipo": m.tipo,
            "quantidade": m.get_quantidade_efetiva(),
            "fornecedor": m.fornecedor,
            "preco_unitario": _to_float(m.preco_unitario),
            "motivo": m.motivo,
            "observacao": m.observacao,
            "movimento_referencia_id": m.movimento_referencia_id,
            "lot_id": m.lot_id,
            "estoque_afetado": m.estoque_afetado,
        }
        for m in movs
    ]


def get_custo_medio(session: Session, product_id: int) -> Optional[float]:
    result = (
        session.query(
            func.sum(StockMovement.preco_total),
            func.sum(StockMovement.quantidade),
        )
        .filter(StockMovement.product_id == product_id)
        .filter(StockMovement.tipo == "entrada")
        .one()
    )

    total_custo, total_qty = result
    if not total_qty or total_qty == 0:
        return None

    return _to_float(total_custo) / _to_float(total_qty)


def get_valor_estoque_total(session: Session) -> float:
    produtos = session.query(Product).all()
    total = 0.0

    for p in produtos:
        qty = get_estoque_total(session, p.id)
        custo = get_custo_medio(session, p.id)
        if qty > 0 and custo:
            total += qty * custo

    return total


# ---------------------------------------------------------------------------
# Dashboard financeiro
# ---------------------------------------------------------------------------


def get_total_receita(db) -> float:
    return _to_float(db.query(func.sum(Sale.valor_total)).scalar())


def get_total_investido(db) -> float:
    total = db.query(
        func.sum(
            case(
                (
                    StockMovement.tipo.in_(["entrada", "estorno"]),
                    StockMovement.quantidade * StockMovement.preco_unitario,
                ),
                (
                    (StockMovement.tipo == "ajuste")
                    & (StockMovement.direcao == "saida"),
                    -(StockMovement.quantidade * StockMovement.preco_unitario),
                ),
                (
                    (StockMovement.tipo == "ajuste")
                    & (StockMovement.direcao == "entrada"),
                    StockMovement.quantidade * StockMovement.preco_unitario,
                ),
                else_=0,
            )
        )
    ).scalar()
    return _to_float(total)


def get_total_gastos(db) -> float:
    return _to_float(db.query(func.sum(Expense.valor)).scalar())


def get_total_vendas(db) -> int:
    return int(db.query(func.count(Sale.id)).scalar() or 0)


def get_lucro_estimado(db) -> float:
    return get_total_receita(db) - get_total_investido(db) - get_total_gastos(db)