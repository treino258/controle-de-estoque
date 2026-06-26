from __future__ import annotations

from sqlalchemy.orm import Session, selectinload

from app.models import Product
from app.models.recipes import RecipeItem


def get_product(session: Session, product_id: int) -> Product | None:
    return session.get(Product, product_id)


def list_products(session: Session) -> list[Product]:
    return session.query(Product).order_by(Product.nome).all()


def list_products_with_recipe_relationships(session: Session) -> list[Product]:
    return (
        session.query(Product)
        .options(
            selectinload(Product.movements),
            selectinload(Product.lots),
            selectinload(Product.recipe_items).selectinload(RecipeItem.ingredient),
            selectinload(Product.ingredient_in_recipes),
            selectinload(Product.sales),
        )
        .order_by(Product.nome)
        .all()
    )


def list_active_products(session: Session) -> list[Product]:
    return (
        session.query(Product)
        .filter(Product.ativo.is_(True))
        .order_by(Product.nome.asc())
        .all()
    )


def add_product(session: Session, product: Product) -> None:
    session.add(product)


def delete_product(session: Session, product: Product) -> None:
    session.delete(product)
