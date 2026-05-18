import pandas as pd
import streamlit as st

from app.database.connection import SessionLocal
from app.services.inventory_service import (
    get_current_stock_by_product,
    get_expiring_products,
    get_low_stock_products,
    get_total_spent_by_product,
)

st.header("3) Dashboard de Estoque")

# A interface apenas pede dados para o service,
# e o service aplica regras de negócio.
db = SessionLocal()

stock_data = get_current_stock_by_product(db)
low_stock = get_low_stock_products(db)
expiring = get_expiring_products(db, days=7)
total_spent = get_total_spent_by_product(db)

st.subheader("Estoque atual por produto")
if stock_data:
    st.dataframe(pd.DataFrame(stock_data), use_container_width=True)
else:
    st.info("Nenhum produto cadastrado.")

st.subheader("Produtos abaixo do estoque mínimo")
if low_stock:
    st.dataframe(pd.DataFrame(low_stock), use_container_width=True)
else:
    st.success("Nenhum produto abaixo do estoque mínimo.")

st.subheader("Produtos próximos da validade (7 dias)")
if expiring:
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Produto": p.product.nome,
                    "Quantidade": p.quantidade,
                    "Validade": p.data_validade,
                    "Fornecedor": p.fornecedor,
                }
                for p in expiring
            ]
        ),
        use_container_width=True,
    )
else:
    st.info("Nenhum produto próximo da validade nos próximos 7 dias.")

st.subheader("Total gasto por produto")
if total_spent:
    st.dataframe(pd.DataFrame(total_spent), use_container_width=True)
else:
    st.info("Sem dados de gastos ainda.")

db.close()
