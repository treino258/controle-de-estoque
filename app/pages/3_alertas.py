import pandas as pd
import streamlit as st
st.set_page_config(
    page_title="Controle de Estoque",
    layout="wide",
    initial_sidebar_state="expanded",
)

from datetime import date

from app.database.connection import SessionLocal
from app.services.inventory_service import (
    get_current_stock_by_product,
    get_expiring_products,
    get_low_stock_products,
    get_total_spent_by_product,
    get_expired_products,
)



# A interface apenas pede dados para o service,
# e o service aplica regras de negócio.
db = SessionLocal()

stock_data = get_current_stock_by_product(db)
low_stock = get_low_stock_products(db)
expiring = get_expiring_products(db, days=7)
expired = get_expired_products(db)
total_spent = get_total_spent_by_product(db)
df = pd.DataFrame(total_spent)
total_geral = df["preco_total"].sum() if not df.empty else 0





# =========================
# ESTOQUE CRÍTICO
# =========================

st.subheader("Produtos abaixo do estoque mínimo")

if low_stock:

    for product in low_stock:

        st.error(
            f"🚨 {product['nome']} está abaixo do estoque mínimo "
            f"({product['estoque_atual']} em estoque)"
        )

else:
    st.success("✅ Nenhum produto abaixo do estoque mínimo.")


# =========================
# PRODUTOS PRÓXIMOS DA VALIDADE
# =========================

st.subheader("Produtos próximos da validade (7 dias)")

if expiring:

    today = date.today()

    for product in expiring:

        dias_restantes = (
            product.data_validade - today
        ).days

        mensagem = (
            f"{product.product.nome} vence em "
            f"{dias_restantes} dias"
        )

        # Prioridade visual
        if dias_restantes <= 1:
            st.error(f"🚨 {mensagem}")

        elif dias_restantes <= 3:
            st.warning(f"⚠️ {mensagem}")

        else:
            st.info(f"ℹ️ {mensagem}")

else:
    st.success(
        "✅ Nenhum produto próximo da validade nos próximos 7 dias."
    )


# =========================
# produtos expirados
# =========================
st.subheader("Produtos expirados")

if expired:


    today = date.today()

    for product in expired:
        dias_restantes = (
                product.data_validade - today
            ).days
    
        if dias_restantes <= 0:

            st.error(
                f"🚨 {product.product.nome} expirou há "
                f"{-dias_restantes} dias"
            )
else:

    st.success("✅ Nenhum produto expirado.")
