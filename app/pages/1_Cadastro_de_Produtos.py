import streamlit as st
from sqlalchemy.exc import IntegrityError

from app.database.connection import SessionLocal
from app.models.product import Product
from app.services.inventory_service import create_product

st.header("1) Cadastro de Produtos")
st.write(
    "Produtos com tamanhos diferentes (ex.: Cookie 100g e 200g) "
    "devem ser cadastrados separadamente."
)

with st.form("form_produto"):
    nome = st.text_input("Nome do produto")
    categoria = st.selectbox(
        "Categoria", ["matéria-prima", "produto final", "consumível"]
    )
    unidade_medida = st.text_input("Unidade de medida (ex.: litro, kg, unidade)")
    estoque_minimo = st.number_input("Estoque mínimo", min_value=0.0, step=1.0)
    submitted = st.form_submit_button("Salvar produto")

if submitted:
    db = SessionLocal()
    try:
        create_product(db, nome, categoria, unidade_medida, estoque_minimo)
        st.success("Produto cadastrado com sucesso!")
    except IntegrityError:
        db.rollback()
        st.error("Já existe um produto com esse nome.")
    finally:
        db.close()

st.subheader("Produtos cadastrados")
db = SessionLocal()
products = db.query(Product).order_by(Product.nome).all()
db.close()

if products:
    st.dataframe(
        [
            {
                "ID": p.id,
                "Nome": p.nome,
                "Categoria": p.categoria,
                "Unidade": p.unidade_medida,
                "Estoque mínimo": p.estoque_minimo,
            }
            for p in products
        ],
        use_container_width=True,
    )
else:
    st.info("Nenhum produto cadastrado ainda.")
