from datetime import date

import streamlit as st

from app.database.connection import SessionLocal

from app.services.inventory_service import (
    get_produtos_abaixo_minimo,
    get_abertos_proximos_vencimento,
    get_historico_produto,
)

st.set_page_config(
    page_title="Alertas Operacionais",
    layout="wide",
)

st.title("🚨 Alertas Operacionais")

st.caption(
    "Produtos que precisam de atenção imediata."
)

db = SessionLocal()

# =========================================================
# ESTOQUE BAIXO
# =========================================================

st.subheader("📉 Produtos abaixo do estoque mínimo")

baixo_minimo = get_produtos_abaixo_minimo(db)

if baixo_minimo:

    for p in baixo_minimo:

        st.error(
            f"{p['nome']} "
            f"({p['estoque_total']} {p['unidade_medida']}) "
            f"abaixo do mínimo "
            f"({p['estoque_minimo']})"
        )

else:

    st.success(
        "✅ Nenhum produto abaixo do estoque mínimo."
    )

# =========================================================
# PRODUTOS ABERTOS PRÓXIMOS DO VENCIMENTO
# =========================================================

st.subheader("⏳ Produtos abertos próximos do vencimento")

proximos = get_abertos_proximos_vencimento(
    db,
    dias=3,
)

if proximos:

    for item in proximos:

        dias = item["dias_restantes"]

        mensagem = (
            f"{item['produto']} "
            f"vence em {dias} dias "
            f"({item['quantidade']} unidades abertas)"
        )

        if dias <= 1:

            st.error(f"🚨 {mensagem}")

        else:

            st.warning(f"⚠️ {mensagem}")

else:

    st.success(
        "✅ Nenhum produto aberto próximo do vencimento."
    )

# =========================================================
# MOVIMENTAÇÕES CORRIGIDAS
# =========================================================

st.subheader("↩️ Correções recentes")

produtos = [
    p for p in get_produtos_abaixo_minimo(db)
]

movimentos_corrigidos = []

# busca simplificada
# MVP aceitável

from app.models import StockMovement

ajustes = (
    db.query(StockMovement)
    .filter(
        StockMovement.tipo == "ajuste"
    )
    .filter(
        StockMovement.movimento_referencia_id.isnot(None)
    )
    .order_by(
        StockMovement.data_movimento.desc()
    )
    .limit(10)
    .all()
)

if ajustes:

    for a in ajustes:

        direcao = (
            "➕" if a.direcao == "entrada"
            else "➖"
        )

        st.info(
            f"{direcao} "
            f"{a.product.nome} | "
            f"{a.quantidade} | "
            f"{a.motivo}"
        )

else:

    st.success(
        "✅ Nenhuma correção recente."
    )

# =========================================================
# RESUMO RÁPIDO
# =========================================================

st.divider()

st.subheader("📌 Resumo do dia")

qtd_criticos = len(baixo_minimo)
qtd_vencendo = len(proximos)

col1, col2 = st.columns(2)

with col1:

    st.metric(
        "Produtos abaixo do mínimo",
        qtd_criticos,
    )

with col2:

    st.metric(
        "Produtos próximos do vencimento",
        qtd_vencendo,
    )

db.close()