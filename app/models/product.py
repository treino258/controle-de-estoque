"""Modelo de produtos."""

from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    Float,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.enums import ProductType
from app.models.mixins import TenantMixin, TimestampMixin


class Product(TenantMixin, TimestampMixin, Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    nome = Column(
        String,
        nullable=False,
        index=True,
    )

    tipo_produto = Column(
        Enum(
            ProductType,
            name="product_type",
        ),
        nullable=False,
        default="materia_prima",
    )

    unidade_medida = Column(
        String,
        nullable=False,
    )

    estoque_minimo = Column(
        Float,
        nullable=False,
        default=0,
    )

    ativo = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    controla_abertura = Column(
        Boolean,
        default=False,
    )

    validade_apos_abertura = Column(
        Integer,
        nullable=True,
    )

    preco_venda = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Preço de venda para produtos finais e receitas",
    )

    # RELACIONAMENTOS EXISTENTES

    movements = relationship(
        "StockMovement",
        back_populates="product",
        foreign_keys="StockMovement.product_id",
    )

    lots = relationship(
        "StockLot",
        back_populates="product",
        foreign_keys="StockLot.product_id",
    )

    sales = relationship(
        "Sale",
        back_populates="product",
    )

    # NOVOS RELACIONAMENTOS DE RECEITA

    recipe_items = relationship(
        "RecipeItem",
        foreign_keys="RecipeItem.recipe_id",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeItem.recipe_id" 
    )

    ingredient_in_recipes = relationship(
        "RecipeItem",
        foreign_keys="RecipeItem.ingredient_id",
        back_populates="ingredient",
        
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "nome",
            name="uq_product_tenant_nome",
        ),
    )

    def __repr__(self):
        return (
            f"<Product "
            f"id={self.id} "
            f"nome={self.nome!r} "
            f"tipo={self.tipo_produto}>"
        )

    @property
    def is_receita(self) -> bool:
        return self.tipo_produto == "receita"


    @property
    def is_materia_prima(self) -> bool:
        return self.tipo_produto == "materia_prima"


    @property
    def is_produto_final(self) -> bool:
        return self.tipo_produto == "produto_final"


    @property
    def is_consumivel(self) -> bool:
        return self.tipo_produto == "consumivel"