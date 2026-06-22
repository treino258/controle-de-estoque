from __future__ import annotations


from sqlite3 import IntegrityError
from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database.seed import DEFAULT_TENANT_ID
from app.models import Product



def _get_product(session: Session, product_id: int) -> Product:
    produto = session.get(Product, product_id)
    if not produto:
        raise ValueError("Produto não encontrado.")
    return produto



def criar_produto(
    session: Session,
    nome: str,
    tipo_produto: str,
    unidade_medida: str,
    estoque_minimo: float,
    controla_abertura: bool,
    preco_venda: Optional[float] = None,
    validade_apos_abertura: Optional[int] = None,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> Product:

    if tipo_produto not in (
        "materia_prima",
        "consumivel",
        "produto_final",
        "receita",
    ):
        raise ValueError(
            "Tipo de produto inválido."
        )

    if tipo_produto in (
        "produto_final",
        "receita",
    ):
        controla_abertura = False
        validade_apos_abertura = None

    produto = Product(
        tenant_id=tenant_id,
        nome=nome.strip(),
        tipo_produto=tipo_produto,
        unidade_medida=unidade_medida,
        estoque_minimo=estoque_minimo,
        controla_abertura=controla_abertura,
        validade_apos_abertura=validade_apos_abertura,
        preco_venda=preco_venda,
    )

    session.add(produto)
    session.commit()
    session.refresh(produto)

    return produto

# ---------------------------------------------------------------------------
# desativar / atualizar
# ---------------------------------------------------------------------------

def desativar_produto(session: Session, product_id: int) -> Product:
    produto = _get_product(session, product_id)
    produto.ativo = not produto.ativo
    session.commit()
    session.refresh(produto)
    return produto


def delete_product(
    session: Session,
    product_id: int,
) -> None:
    try:
        produto = _get_product(session, product_id)

        if produto.movements:
            raise ValueError(
                "Este produto possui movimentações registradas."
            )

        if produto.lots:
            raise ValueError(
                "Este produto possui lotes vinculados."
            )

        # Produto é uma receita
        if produto.recipe_items:
            raise ValueError(
                "Esta receita possui ingredientes cadastrados."
            )

        # Produto é usado como ingrediente
        if produto.ingredient_in_recipes:
            raise ValueError(
                "Este produto é utilizado em uma ou mais receitas."
            )

        session.delete(produto)
        session.commit()

    except IntegrityError:
        session.rollback()

        raise ValueError(
            "Não foi possível excluir o produto porque existem registros relacionados a ele."
        )
    
def pode_excluir(produto) -> bool:
    return (
        not produto.movements
        and not produto.lots
        and not produto.recipe_items
        and not produto.ingredient_in_recipes
    )