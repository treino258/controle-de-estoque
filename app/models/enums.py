from enum import Enum


class ProductType(str, Enum):
    MATERIA_PRIMA = "materia_prima"
    CONSUMIVEL = "consumivel"
    PRODUTO_FINAL = "produto_final"
    RECEITA = "receita"