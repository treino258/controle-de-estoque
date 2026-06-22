from sqlalchemy import (
    Column,
    Float,
    Integer,
    ForeignKey,
    UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.database.connection import Base
from app.models.mixins import TenantMixin, TimestampMixin





class RecipeItem(TenantMixin, TimestampMixin, Base):
    __tablename__ = "recipe_items"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    recipe_id = Column(
        Integer,
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    ingredient_id = Column(
        Integer,
        ForeignKey(
            "products.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    quantity = Column(
        Float,
        nullable=False,
    )

    recipe = relationship(
        "Product",
        foreign_keys=[recipe_id],
        back_populates="recipe_items",
    )

    ingredient = relationship(
        "Product",
        foreign_keys=[ingredient_id],
        back_populates="ingredient_in_recipes",
    )

    __table_args__ = (
        UniqueConstraint(
            "recipe_id",
            "ingredient_id",
            name="uq_recipe_ingredient",
        ),
    )

    def __repr__(self):
        return (
            f"<RecipeItem "
            f"recipe={self.recipe_id} "
            f"ingredient={self.ingredient_id} "
            f"qty={self.quantity}>"
        )