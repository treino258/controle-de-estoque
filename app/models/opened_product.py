from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String
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


    # aberto | consumido | vencido | estornado
    status = Column(
        String,
        nullable=False,
        default="aberto",
    )

    product = relationship("Product")

    purchase = relationship("Purchase")