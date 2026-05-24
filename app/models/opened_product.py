from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.database.connection import Base


class OpenedProduct(Base):

    __tablename__ = "opened_products"

    id = Column(Integer, primary_key=True)

    produto_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
    )

    purchase_id = Column(
        Integer,
        ForeignKey("purchases.id"),
        nullable=False,
    )

    data_abertura = Column(
        Date,
        nullable=False,
    )

    validade_aberto = Column(
        Date,
        nullable=False,
    )

    quantidade = Column(
        Integer,
        nullable=False,
        default=1,
    )

    finalizado = Column(
        Boolean,
        default=False,
    )

    estornado = Column(
        Boolean, 
        default=False
    )

    product = relationship("Product")

    purchase = relationship("Purchase")