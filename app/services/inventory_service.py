"""Regras de negócio de estoque e dashboard.

Camada de service concentra regras para não acoplar
lógica de negócio na interface (Streamlit pages).
"""

from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.purchase import Purchase


def create_product(
    db: Session,
    nome: str,
    categoria: str,
    unidade_medida: str,
    estoque_minimo: float,
) -> Product:
    product = Product(
        nome=nome.strip(),
        categoria=categoria,
        unidade_medida=unidade_medida.strip(),
        estoque_minimo=estoque_minimo,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def register_purchase(
    db: Session,
    produto_id: int,
    quantidade: float,
    preco_unitario: float,
    data_compra: date,
    data_validade: date | None,
    fornecedor: str | None,
    tempo_entrega: int | None,
) -> Purchase:
    # Preço total calculado automaticamente para evitar entrada manual incorreta.
    preco_total = quantidade * preco_unitario

    purchase = Purchase(
        produto_id=produto_id,
        quantidade=quantidade,
        preco_unitario=preco_unitario,
        preco_total=preco_total,
        data_compra=data_compra,
        data_validade=data_validade,
        fornecedor=fornecedor.strip() if fornecedor else None,
        tempo_entrega=tempo_entrega,
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)
    return purchase


def get_current_stock_by_product(db: Session) -> list[dict]:
    """Calcula estoque atual a partir da soma das compras."""
    rows = (
        db.query(
            Product.id,
            Product.nome,
            Product.categoria,
            Product.unidade_medida,
            Product.estoque_minimo,
            func.coalesce(func.sum(Purchase.quantidade), 0).label("estoque_atual"),
        )
        .outerjoin(Purchase, Purchase.produto_id == Product.id)
        .group_by(Product.id)
        .order_by(Product.nome)
        .all()
    )

    return [
        {
            "produto_id": row.id,
            "nome": row.nome,
            "categoria": row.categoria,
            "unidade_medida": row.unidade_medida,
            "estoque_minimo": row.estoque_minimo,
            "estoque_atual": row.estoque_atual,
        }
        for row in rows
    ]


def get_low_stock_products(db: Session) -> list[dict]:
    stock_data = get_current_stock_by_product(db)
    return [item for item in stock_data if item["estoque_atual"] < item["estoque_minimo"]]


def get_expiring_products(db: Session, days: int = 7) -> list[Purchase]:
    """Retorna compras com validade nos próximos N dias."""
    today = date.today()
    limit_date = today + timedelta(days=days)

    return (
        db.query(Purchase)
        .join(Product, Product.id == Purchase.produto_id)
        .filter(Purchase.data_validade.isnot(None))
        .filter(Purchase.data_validade >= today)
        .filter(Purchase.data_validade <= limit_date)
        .order_by(Purchase.data_validade)
        .all()
    )


def get_total_spent_by_product(db: Session) -> list[dict]:
    rows = (
        db.query(
            Product.nome,
            func.coalesce(func.sum(Purchase.preco_total), 0).label("total_gasto"),
        )
        .outerjoin(Purchase, Purchase.produto_id == Product.id)
        .group_by(Product.id)
        .order_by(Product.nome)
        .all()
    )
    return [{"nome": row.nome, "total_gasto": row.total_gasto} for row in rows]
