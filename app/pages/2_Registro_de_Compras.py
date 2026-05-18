from datetime import date

import streamlit as st

from app.database.connection import SessionLocal
from app.models.product import Product
from app.models.purchase import Purchase
from app.services.inventory_service import register_purchase

st.header("2) Registro de Compras")
st.write("O preço total é calculado automaticamente: quantidade * preço unitário.")

db = SessionLocal()
products = db.query(Product).order_by(Product.nome).all()

if not products:
    st.warning("Cadastre pelo menos um produto antes de registrar compras.")
    db.close()
    st.stop()

product_options = {f"{p.nome} ({p.unidade_medida})": p.id for p in products}

with st.form("form_compra"):
    product_label = st.selectbox("Produto", list(product_options.keys()))
    quantidade = st.number_input("Quantidade", min_value=0.01, step=1.0)
    preco_unitario = st.number_input("Preço unitário (R$)", min_value=0.01, step=0.5)
    data_compra = st.date_input("Data da compra", value=date.today())
    data_validade = st.date_input("Data de validade", value=None)
    fornecedor = st.text_input("Fornecedor")
    tempo_entrega = st.number_input("Tempo de entrega (dias)", min_value=0, step=1)

    submitted = st.form_submit_button("Registrar compra")

if submitted:
    purchase = register_purchase(
        db=db,
        produto_id=product_options[product_label],
        quantidade=quantidade,
        preco_unitario=preco_unitario,
        data_compra=data_compra,
        data_validade=data_validade,
        fornecedor=fornecedor,
        tempo_entrega=tempo_entrega,
    )
    st.success(f"Compra registrada! Preço total calculado: R$ {purchase.preco_total:.2f}")

st.subheader("Últimas compras")
purchases = db.query(Purchase).order_by(Purchase.data_compra.desc(), Purchase.id.desc()).limit(20)

st.dataframe(
    [
        {
            "ID": p.id,
            "Produto": p.product.nome,
            "Quantidade": p.quantidade,
            "Preço unitário": p.preco_unitario,
            "Preço total": p.preco_total,
            "Data compra": p.data_compra,
            "Validade": p.data_validade,
            "Fornecedor": p.fornecedor,
            "Tempo entrega (dias)": p.tempo_entrega,
        }
        for p in purchases
    ],
    use_container_width=True,
)

db.close()
