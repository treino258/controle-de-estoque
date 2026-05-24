# Controle de Estoque para Cafeteria (MVP - Fase 1)

Projeto simples e didático para controle de estoque e compras.

## Tecnologias
- Python
- Streamlit (interface)
- SQLite (banco local)
- SQLAlchemy (ORM)

## Estrutura de pastas

```text
app/
  app.py                    # ponto de entrada Streamlit
  database/
    connection.py           # engine e sessões SQLAlchemy
    init_db.py              # criação das tabelas
  models/
    base.py                 # Base declarativa do SQLAlchemy
    product.py              # tabela de produtos
    purchase.py             # tabela de compras (eventos)
  services/
    inventory_service.py    # regras de negócio de estoque e dashboard
  pages/
    1_Cadastro_de_Produtos.py
    2_Registro_de_Compras.py
    3_Dashboard.py
```

## Como rodar localmente

1. Crie e ative um ambiente virtual.
2. Instale dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Rode o Streamlit:
   ```bash
   streamlit run app/main.py
   ```
4. Abra no navegador o endereço mostrado no terminal (normalmente http://localhost:8501).

## Fluxo dos dados

1. O usuário cadastra produtos em `products`.
2. O usuário registra compras em `purchases`.
3. Cada compra gera uma movimentação com quantidade e custo.
4. O dashboard calcula estoque atual por soma das movimentações.

## Por que separar Product e Purchase?

- `Product`: informações permanentes do item (nome, categoria, unidade, estoque mínimo).
- `Purchase`: eventos históricos de compra (quando, quanto, custo, fornecedor).

Essa separação evita perda de histórico e prepara a base para análises futuras.

## Por que o estoque é calculado e não salvo manualmente?

Salvar estoque manualmente pode gerar inconsistências. Exemplo: uma compra registrada e estoque não atualizado.

Calculando a partir das movimentações, temos:
- rastreabilidade
- histórico auditável
- menor risco de erro humano

## O que é SQLAlchemy e ORM?

- **ORM (Object-Relational Mapping)**: técnica para mapear tabelas do banco para classes Python.
- **SQLAlchemy**: biblioteca que implementa ORM e também recursos SQL avançados.

Com ele, escrevemos código Python para manipular dados sem depender de SQL puro em toda parte.
