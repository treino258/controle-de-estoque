from datetime import date

import streamlit as st

st.set_page_config(
    page_title="Controle de Estoque",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd


from app.utils.ui_formater import (
    format_price_variation,
    format_data_compra_badge,
)
from app.utils.data_formater import format_validade
from app.database.connection import SessionLocal
from app.models import Product
from app.models import Purchase
from app.services.inventory_service import register_purchase, delete_purchase, get_total_spent_by_product

db = SessionLocal()

previous_prices = {}

total_spent = get_total_spent_by_product(db)
df = pd.DataFrame(total_spent)
total_geral = df["preco_total"].sum() if not df.empty else 0

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
purchases = db.query(Purchase).order_by(Purchase.data_compra.desc(), Purchase.id.desc()).limit(20).all()



busca = st.text_input(
    "🔍 Buscar compra"
)

if busca:

    busca = busca.lower()

    purchases = [
        p for p in purchases
        if (
            # Produto
            busca in p.product.nome.lower()

            # Fornecedor
            or busca in (p.fornecedor or "").lower()

            # Quantidade
            or busca in str(p.quantidade).lower()

            # Preço unitário
            or busca in str(p.preco_unitario).lower()

            # Preço total
            or busca in str(p.preco_total).lower()

            # Data validade
            or busca in str(p.data_validade).lower()

            # Data compra
            or busca in str(p.data_compra).lower()

            # Tempo entrega
            or busca in str(p.tempo_entrega).lower()
        )
    ]



# Cabeçalho
header1, header2, header3, header4, header5, header6, header7, header8, header9 = st.columns(
    [1.5, 1, 1, 1, 1, 1, 1, 1, 0.90]
)

header1.markdown("**Produto**")
header2.markdown("**Quantidade**")
header3.markdown("**Preço Unitário**")
header4.markdown("**Preço Total**")
header5.markdown("**Data da compra**")
header6.markdown("**Validade**")
header7.markdown("**Fornecedor**")
header8.markdown("**Tempo de entrega**")
header9.markdown("**Excluir**")

previous_prices = {}

# Linhas
for purchase in purchases:
    with st.container(border=True):
        col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns(
        [1.5, 1, 1, 1, 1, 1, 1, 1, 0.75]
        )

        col1.write(purchase.product.nome)
        col2.write(purchase.quantidade)
        previous_price = previous_prices.get(
        purchase.produto_id)
        col3.markdown(format_price_variation(purchase.preco_unitario,previous_price),unsafe_allow_html=True,)
        col4.write(f"R$ {purchase.preco_total:.2f}")
        col5.markdown(format_data_compra_badge(purchase.data_compra),unsafe_allow_html=True,)
        col6.markdown(format_validade(purchase.data_validade),unsafe_allow_html=True,)
        col7.write(purchase.fornecedor)
        col8.write(f"{purchase.tempo_entrega} dias")

        previous_prices[purchase.produto_id] = (purchase.preco_unitario)

        if col9.button(
            "🗑️",
            key=f"delete_purchase_{purchase.id}",
        ):

            delete_purchase(db, purchase.id)

            st.success("Compra excluída com sucesso!")

            st.rerun()
        


db.close()


if total_spent:
    st.markdown(f"### TOTAL : R$ {total_geral:.2f}")
else:
    st.info("Sem dados de gastos ainda.")
