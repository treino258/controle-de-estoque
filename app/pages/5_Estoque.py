from datetime import date

import streamlit as st
from sqlalchemy import func, delete

from app.database.connection import SessionLocal
from app.models import OpenedProduct
from app.services.inventory_service import (
    get_current_stock_by_product,
    open_product, revert_opened_product,
)

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="Controle de Estoque",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📦 Controle de Estoque")

db = SessionLocal()

stock_data = get_current_stock_by_product(db)

# =========================================================
# PRODUTOS ABERTOS (MAP)
# =========================================================

opened_products = (
    db.query(OpenedProduct)
    .order_by(OpenedProduct.validade_aberto.asc())
    .all()
)

opened_map = {}
for o in opened_products:
    opened_map.setdefault(o.produto_id, []).append(o)

# =========================================================
# FILTRO
# =========================================================

st.subheader("📊 Estoque atual")

busca = st.text_input("🔍 Buscar produto")

if stock_data:

    if busca:
        stock_data = [
            p for p in stock_data
            if busca.lower() in p["nome"].lower()
        ]

    # =========================================================
    # HEADER FIXO (mais “clean”)
    # =========================================================

    col = st.columns([4, 2, 1.2, 1.2, 1.2, 1.2, 1.4])

    col[0].markdown("**🧾 Produto**")
    col[1].markdown("**📁 Categoria**")
    col[2].markdown("**📦 Estoque**")
    col[3].markdown("**⚠️ Mín**")
    col[4].markdown("**🧊 Abertos**")
    col[5].markdown("**Qtd**")
    col[6].markdown("**Abrir**")

    st.divider()

    # =========================================================
    # LINHAS
    # =========================================================

    for item in stock_data:

        produto_id = item["produto_id"]
        total_aberto = sum(o.quantidade for o in opened_map.get(produto_id, []))

        col = st.columns([4, 2, 1.2, 1.2, 1.2, 1.2, 1.4])

        # -------------------------
        # INFO PRODUTO (fonte maior)
        # -------------------------

        col[0].markdown(f"<span style='font-size:30px'><b>{item['nome']}</b>  \n<span style='font-size:15px;color:gray'>{item['unidade_medida']}</span>", unsafe_allow_html=True)

        col[1].markdown(f"<span style='font-size:20px'>{item['categoria']}</span>", unsafe_allow_html=True)

        col[2].markdown(f"<span style='font-size:20px;font-weight:600'>{item['estoque_atual']}</span>", unsafe_allow_html=True)

        col[3].markdown(f"<span style='font-size:20px'>{item['estoque_minimo']}</span>", unsafe_allow_html=True)

        col[4].markdown(
            f"<span style='font-size:20px'>{total_aberto}</span>",
            unsafe_allow_html=True,
        )

        # -------------------------
        # CONTROLE DE ABERTURA (menor e mais compacto)
        # -------------------------

        controla = item.get("controla_abertura", False)
        estoque = item["estoque_atual"]

        if controla and estoque > 0:

            qtd = col[5].number_input(
                "",
                min_value=1,
                max_value=max(1, int(estoque)),
                value=1,
                key=f"qtd_{produto_id}",
                label_visibility="collapsed",
            )

            if col[6].button(
                "Abrir",
                key=f"open_{produto_id}",
                use_container_width=True,
            ):
                open_product(db, produto_id, qtd)

                st.success(f"Produto aberto ({qtd})!")
                st.rerun()

        else:
            col[5].write("-")
            col[6].write("")

        st.divider()





# =========================================================
# PRODUTOS ABERTOS
# =========================================================

st.header("🧊 Produtos Abertos")

if opened_products:

    for opened in opened_products:

        produto = next(
            (p for p in stock_data if p["produto_id"] == opened.produto_id),
            None
        )
        lote = opened.purchase_id
        

        if not produto:
            continue

        dias = (opened.validade_aberto - date.today()).days

        with st.container(border=True):

            c1, c2, c3, c4 = st.columns([3, 2, 1, 0.5])

            c1.markdown(f"### {produto['nome']}")

            c2.markdown(
                f"""
                <div style="text-align:center;">
                    <div style="font-size:24px;font-weight:700;">
                        🧊 {opened.quantidade}
                    </div>
                    <div style="color:gray;font-size:13px;">
                        unidades abertas
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if dias <= 0:
                c3.error("🚨 Expirado")
            elif dias <= 3:
                c3.warning(f"⚠️ {dias} dias")
            else:
                c3.success(f"✅ {dias} dias")

            # 🗑️ BOTÃO DELETE INDIVIDUAL
            if c4.button("🗑️", key=f"del_{opened.id}"):
                revert_opened_product(db, opened.id)
                st.warning("Movimentação estornada!")
                st.rerun()

    st.divider()

if st.button("🧹 Remover produtos expirados", type="primary"):
    expirados = [
        o.produto_id
        for o in opened_products
        if (o.validade - date.today()).days <= 0
    ]

    if expirados:
        db.query(OpenedProduct).filter(
            OpenedProduct.produto_id.in_(expirados),
            OpenedProduct.finalizado == False
        ).delete(synchronize_session=False)

        db.commit()

        st.success("Produtos expirados removidos!")
        st.rerun()
    else:
        st.info("Nenhum produto expirado.")

# =========================================================
# FINALIZAÇÃO
# =========================================================

db.close()