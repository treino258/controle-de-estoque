import streamlit as st

st.set_page_config(
    page_title="Controle de Estoque",
    layout="wide",
    initial_sidebar_state="expanded",
)

from sqlalchemy.exc import IntegrityError


from app.database.connection import SessionLocal
from app.models import Product
from app.services.inventory_service import (
    criar_produto,
    desativar_produto,
    delete_product
)

st.header("1) Cadastro de Produtos")
st.write(
    "Produtos com tamanhos diferentes (ex.: Cookie 100g e 200g) "
    "devem ser cadastrados separadamente."
)

controla_abertura = st.checkbox("Controla abertura?")

with st.form("form_produto"):

    nome = st.text_input("Nome do produto")
    categoria = st.selectbox(
        "Categoria", ["matéria-prima", "produto final", "consumível"]
    )
    unidade_medida = st.text_input("Unidade de medida")
    estoque_minimo = st.number_input("Estoque mínimo", min_value=0.0)

    validade_apos_abertura = None
    if controla_abertura:
        validade_apos_abertura = st.number_input(
            "Validade após aberto (dias)",
            min_value=1,
            step=1
        )

    submitted = st.form_submit_button("Salvar produto")

if submitted:

    db = SessionLocal()

    try:
        criar_produto(
            db,
            nome,
            categoria,
            unidade_medida,
            estoque_minimo,
            controla_abertura,
            validade_apos_abertura
        )

        st.success("Produto cadastrado com sucesso!")
        st.rerun()

    except IntegrityError:
        db.rollback()
        st.error("Já existe um produto com esse nome.")

    except Exception as e:
        db.rollback()
        st.error(f"Erro ao salvar produto: {e}")

    finally:
        db.close()

db = SessionLocal()
st.subheader("Produtos cadastrados")
products = db.query(Product).order_by(Product.nome).all()
ativos = [p for p in products if p.ativo]
inativos = [p for p in products if not p.ativo]

if products:

    header1, header2, header3, header4, header5, header6 = st.columns(
        [3, 2, 2, 2, 1, 1]
    )

    header1.markdown("**Nome**")
    header2.markdown("**Categoria**")
    header3.markdown("**Unidade**")
    header4.markdown("**Estoque mínimo**")
    header5.markdown("**Excluir**")
    header6.markdown("**Desativar/Ativar**")

    for product in ativos:

        col1, col2, col3, col4, col5, col6 = st.columns(
            [3, 2, 2, 2, 1, 1]
        )

        col1.write(product.nome)
        col2.write(product.categoria)
        col3.write(product.unidade_medida)
        col4.write(product.estoque_minimo)

        if col5.button(
            "🗑️",
            key=f"delete_{product.id}",
        ):

            db = SessionLocal()

            delete_product(db, product.id)

            db.close()

            st.success(
                f"{product.nome} excluído com sucesso!"
            )

            st.rerun()
        
        if col6.button(
            "🚫" if product.ativo else "Ativar",
            key=f"toggle_{product.id}",
        ):


            estava_ativo = product.ativo

            desativar_produto(db, product.id)


            st.success(
                f"{product.nome} "
                f"{'desativado' if estava_ativo else 'ativado'} com sucesso!"
            )

            st.rerun()
        
    if inativos:

        st.divider()

        st.subheader("Produtos desativados")

        for product in inativos:

            col1, col2, col3, col4, col5, col6 = st.columns(
                [3, 2, 2, 2, 1, 1]
            )

            col1.markdown(
                f"""
                <span style="opacity:0.45">
                    {product.nome}
                </span>
                """,
                unsafe_allow_html=True
            )

            col2.markdown(
                f"""
                <span style="opacity:0.45">
                    {product.categoria}
                </span>
                """,
                unsafe_allow_html=True
            )

            col3.markdown(
                f"""
                <span style="opacity:0.45">
                    {product.unidade_medida}
                </span>
                """,
                unsafe_allow_html=True
            )

            col4.markdown(
                f"""
                <span style="opacity:0.45">
                    {product.estoque_minimo}
                </span>
                """,
                unsafe_allow_html=True
            )

            # EXCLUIR
            if col5.button(
                "🗑️",
                key=f"delete_inactive_{product.id}",
            ):

                delete_product(db, product.id)

                st.success(
                    f"{product.nome} excluído com sucesso!"
                )

                st.rerun()

            # ATIVAR
            if col6.button(
                "Ativar",
                key=f"activate_{product.id}",
            ):

                desativar_produto(db, product.id)

                st.success(
                    f"{product.nome} ativado com sucesso!"
                )

                st.rerun()

else:

    st.info("Nenhum produto cadastrado ainda.")

db.close()