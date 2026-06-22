# scripts/test_seed.py

from random import choice, randint
from faker import Faker

from app.database.connection import SessionLocal
from app.models import Product, ProductType

fake = Faker("pt_BR")

db = SessionLocal()

for i in range(20):

    tipo = choice([
        ProductType.MATERIA_PRIMA,
        ProductType.CONSUMIVEL,
        ProductType.PRODUTO_FINAL,
    ])

    produto = Product(
        tenant_id=1,
        nome=f"{fake.word()}_{i}",
        tipo_produto=tipo,
        unidade_medida=choice(["kg", "l", "un"]),
        estoque_minimo=randint(1, 10),
        controla_abertura=choice([True, False]),
        preco_venda=15.0 if tipo == ProductType.PRODUTO_FINAL else None,
        ativo=True,
    )

    db.add(produto)

db.commit()

print("Produtos criados!")