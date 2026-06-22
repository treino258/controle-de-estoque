from sqlalchemy.orm import Session
from app.models import Product



def listar_receitas_ativas(session:Session) -> list[Product]:
    
    return  (
        session.query(Product)
        .filter(
            Product.tipo_produto == "receita",
            Product.ativo.is_(True),
        )
        .order_by(Product.nome)
        .all()
    )

def listar_ingredientes_disponiveis(session:Session) ->list[Product]:

    return(
        session.query(Product)
        .filter(
            Product.tipo_produto != "receita",
            Product.ativo.is_(True),
        )
        .order_by(Product.nome)
        .all()
    )
    
def buscar_receita_id(session:Session, receita_id: int) -> Product | None:

    return(
        session.query(Product)
        .filter( Product.id == receita_id)
        .first()
    )