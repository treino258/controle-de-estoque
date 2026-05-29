import sqlite3

c = sqlite3.connect("cafeteria_estoque.db")
print("products:", c.execute("SELECT id, nome FROM products").fetchall())
print(
    "open lots:",
    c.execute(
        "SELECT id, product_id, quantidade_atual, status, abertura_movement_id "
        "FROM stock_lots WHERE status='open'"
    ).fetchall(),
)
