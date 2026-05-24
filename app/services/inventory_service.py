"""Regras de negócio de estoque e dashboard.

Camada de service concentra regras para não acoplar
lógica de negócio na interface (Streamlit pages).
"""

from datetime import date, timedelta

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.models import Product, OpenedProduct, Purchase, product



def create_product(
    db: Session,
    nome: str,
    categoria: str,
    unidade_medida: str,
    estoque_minimo: float,
    controla_abertura: bool = False,
    validade_apos_abertura: int | None = None,
) -> Product:
    product = Product(
        nome=nome.strip(),
        categoria=categoria,
        unidade_medida=unidade_medida.strip(),
        estoque_minimo=estoque_minimo,
        controla_abertura=controla_abertura,
        validade_apos_abertura=validade_apos_abertura,
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
    """Estoque real = entradas - saídas"""

    entradas = (
        db.query(
            Purchase.produto_id,
            func.sum(Purchase.quantidade).label("entrada")
        )
        .group_by(Purchase.produto_id)
        .subquery()
    )

    saidas = (
        db.query(
            OpenedProduct.produto_id,
            func.sum(
                case(
                    (OpenedProduct.estornado == False, OpenedProduct.quantidade),
                    else_=0
                )
            ).label("saida")
        )
        .group_by(OpenedProduct.produto_id)
        .subquery()
    )

    rows = (
        db.query(
            Product.id,
            Product.nome,
            Product.categoria,
            Product.unidade_medida,
            Product.estoque_minimo,
            Product.controla_abertura,
            (func.coalesce(entradas.c.entrada, 0) -
             func.coalesce(saidas.c.saida, 0)).label("estoque_atual")
        )
        .outerjoin(entradas, entradas.c.produto_id == Product.id)
        .outerjoin(saidas, saidas.c.produto_id == Product.id)
        .order_by(Product.nome)
        .all()
    )

    return [
        {
            "produto_id": r.id,
            "nome": r.nome,
            "categoria": r.categoria,
            "unidade_medida": r.unidade_medida,
            "estoque_minimo": r.estoque_minimo,
            "controla_abertura": r.controla_abertura,
            "estoque_atual": float(r.estoque_atual or 0),
        }
        for r in rows
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

def get_expired_products(db: Session) -> list[Purchase]:
    """Retorna compras expiradas."""
    today = date.today()

    return (
        db.query(Purchase)
        .join(Product, Product.id == Purchase.produto_id)
        .filter(Purchase.data_validade.isnot(None))
        .filter(Purchase.data_validade < today)
        .order_by(Purchase.data_validade)
        .all()
    )

def get_total_spent_by_product(db: Session) -> list[dict]:
    rows = (
        db.query(
            Product.nome,
            Purchase.quantidade,
            func.coalesce(func.sum(Purchase.preco_total), 0).label("preco_total"),
        )
        .outerjoin(Purchase, Purchase.produto_id == Product.id)
        .group_by(Product.id)
        .order_by(Product.nome)
        .all()
    )
    return [{"nome": row.nome, "quantidade": row.quantidade, "preco_total": row.preco_total} for row in rows]

def delete_product(db: Session, product_id: int):

    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if product:

        # Remove compras relacionadas
        db.query(Purchase).filter(
            Purchase.produto_id == product_id
        ).delete()

        # Remove produto
        db.delete(product)

        db.commit()

def delete_purchase(db: Session, purchase_id: int):

    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()

    if not purchase:
        return

    # impede deletar lote já consumido parcialmente
    used = db.query(OpenedProduct).filter(
        OpenedProduct.purchase_id == purchase_id
    ).first()

    if used:
        raise Exception("Não pode deletar lote já utilizado")

    db.delete(purchase)
    db.commit()      

def open_product(db, product_id: int, quantidade: int):

    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    days = product.validade_apos_abertura if product and product.validade_apos_abertura else 1
    validade_base = date.today() + timedelta(days=int(days))

    purchases = (
        db.query(Purchase)
        .filter(Purchase.produto_id == product_id)
        .filter(Purchase.quantidade > 0)
        .order_by(Purchase.data_validade.asc())
        .all()
    )

    if not purchases:
        return []

    restante = quantidade
    movimentos = []

    for lote in purchases:

        if restante <= 0:
            break

        disponivel = lote.quantidade

        if disponivel <= 0:
            continue

        retirar = min(disponivel, restante)

        movimentos.append(
            OpenedProduct(
                produto_id=product_id,
                purchase_id=lote.id,
                quantidade=retirar,
                data_abertura=date.today(),
                validade_aberto=validade_base,
            )
        )

        db.add(movimentos[-1])
        restante -= retirar

    db.commit()

    return movimentos

def delete_opened_product(db, opened_id: int):
    db.query(OpenedProduct).filter(
        OpenedProduct.id == opened_id
    ).delete()
    db.commit()

def revert_opened_product(db, opened_id: int):

    opened = db.query(OpenedProduct).filter(
        OpenedProduct.id == opened_id
    ).first()

    if not opened:
        return

    opened.estornado = True
    db.commit()