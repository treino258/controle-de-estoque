"""Aplicação Streamlit - MVP de controle de estoque para cafeteria.

Arquitetura escolhida (simples e didática):
- models: define tabelas/classes de domínio.
- database: conexão e inicialização do banco.
- services: regras de negócio.
- pages: interface de cada funcionalidade.

Essa separação facilita manutenção e evolução futura.
"""

import streamlit as st

from app.database.init_db import init_db



st.set_page_config(page_title="Controle de Estoque - Cafeteria", layout="wide")
init_db()

st.title("☕ Controle de Estoque - Cafeteria (MVP Fase 1)")
st.markdown(
    "Use o menu lateral para cadastrar produtos, registrar compras "
    "e acompanhar o dashboard de estoque."
)
