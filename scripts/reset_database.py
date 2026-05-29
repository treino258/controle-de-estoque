"""Recria o banco com o schema atual (apaga dados locais).

Uso:
    python scripts/reset_database.py

Use antes de entregar ao cliente se o SQLite antigo não tiver as novas colunas.
Faça backup de cafeteria_estoque.db se já houver dados importantes.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database.connection import Base, engine  # noqa: E402
from app.database.init_db import init_db  # noqa: E402

DB_PATH = Path("cafeteria_estoque.db")


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removido: {DB_PATH}")

    Base.metadata.drop_all(bind=engine)
    init_db()
    print("Banco recriado com schema atual e tenant padrão.")


if __name__ == "__main__":
    main()
