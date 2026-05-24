import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Dashboard",
    layout="wide",
)

from app.database.connection import SessionLocal
from app.models import Product
from app.models import Purchase
from app.services.inventory_service import (
    get_expired_products,
    get_low_stock_products,
    get_total_spent_by_product,
)

st.header("📊 Dashboard")

db = SessionLocal()

# Dados
products = db.query(Product).all()
purchases = db.query(Purchase).all()

low_stock = get_low_stock_products(db)

expired = get_expired_products(db)

total_spent = get_total_spent_by_product(db)

df_total = pd.DataFrame(total_spent)

# KPIs
total_gasto = (
    df_total["preco_total"].sum()
    if not df_total.empty
    else 0
)

total_produtos = len(products)

total_compras = len(purchases)

total_alertas = len(low_stock + expired)

# Cards
col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "💰 Total gasto",
    f"R$ {total_gasto:.2f}",
)

col2.metric(
    "📦 Produtos",
    total_produtos,
)

col3.metric(
    "🛒 Compras",
    total_compras,
)

col4.metric(
    "⚠️ Alertas",
    total_alertas,
)

st.divider()