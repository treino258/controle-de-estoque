"""Modelo central de movimentações de estoque.

Substitui Purchase e OpenedProduct por uma tabela única de eventos.

Por que uma tabela única?
- Histórico auditável completo: cada mudança no estoque é um registro imutável
- Estoque calculado por soma de movimentações (nunca salvo diretamente)
- Pronto para análises e ML: cada evento tem contexto, timestamp e custo
- Sem inconsistência: não existe estoque "manual" que pode dessincronizar

Tipos de movimentação e seus efeitos:
    entrada  → +quantidade no estoque fechado (compra do fornecedor)
    abertura → -quantidade do fechado, inicia uso (abre uma unidade)
    consumo  → -quantidade do estoque em uso (produto usado/esgotado)
    perda    → -quantidade do fechado ou em uso (venceu, caiu, danificou)
    ajuste   → correção manual (+/-), sempre com motivo registrado
    estorno  → +quantidade, desfaz uma movimentação anterior

Direção de cada tipo (para cálculo de estoque):
    POSITIVO (+): entrada, estorno, ajuste com direcao="entrada"
    NEGATIVO (-): abertura, consumo, perda, ajuste com direcao="saida"
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.database.connection import Base

# Tipos que sempre somam ao estoque
TIPOS_ENTRADA = {"entrada", "estorno"}

# Tipos que sempre subtraem do estoque
TIPOS_SAIDA = {"abertura", "consumo", "perda"}

# Tipos que precisam de direção explícita
TIPOS_COM_DIRECAO = {"ajuste"}


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # O que aconteceu
    tipo = Column(
        Enum(
            "entrada",
            "abertura",
            "consumo",
            "perda",
            "ajuste",
            "estorno",
            name="movement_type",
        ),
        nullable=False,
    )

    # Sempre positivo — a direção é determinada pelo tipo + direcao
    quantidade = Column(Float, nullable=False)

    # Só relevante para ajuste (entrada/saida); outros tipos têm direção fixa
    direcao = Column(
        Enum("entrada", "saida", name="movement_direction"),
        nullable=True,
    )

    # --- Campos de entrada (compra) ---
    preco_unitario = Column(Float, nullable=True)
    preco_total = Column(Float, nullable=True)
    fornecedor = Column(String, nullable=True)
    tempo_entrega = Column(Integer, nullable=True)  # dias (útil para ML)
    data_validade = Column(Date, nullable=True)     # validade do lote comprado

    # --- Campos de abertura ---
    validade_aberto = Column(Date, nullable=True)   # validade após abrir

    # Referência à movimentação de entrada que originou esta abertura
    # Útil para FEFO (First Expired, First Out) e rastreabilidade de lote
    entrada_origem_id = Column(
        Integer,
        ForeignKey("stock_movements.id"),
        nullable=True,
    )

    # --- Campos de perda e ajuste ---
    motivo = Column(String, nullable=True)  # obrigatório para perda e ajuste

    # --- Metadados ---
    data_movimento = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    observacao = Column(String, nullable=True)

    # Relacionamentos
    product = relationship("Product", back_populates="movements")
    entrada_origem = relationship("StockMovement", remote_side=[id])

    # Constraints de integridade
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="quantidade_positiva"),
        CheckConstraint(
            """
            (tipo = 'ajuste' AND direcao IS NOT NULL)
            OR (tipo != 'ajuste' AND direcao IS NULL)
            """,
            name="ajuste_precisa_direcao",
        ),
    )

    def get_sinal(self) -> int:
        """Retorna +1 ou -1 para cálculo de estoque."""
        if self.tipo in TIPOS_ENTRADA:
            return +1
        if self.tipo in TIPOS_SAIDA:
            return -1
        if self.tipo == "ajuste":
            return +1 if self.direcao == "entrada" else -1
        raise ValueError(f"Tipo desconhecido: {self.tipo}")

    def get_quantidade_efetiva(self) -> float:
        """Quantidade com sinal para somar diretamente no cálculo de estoque."""
        return self.quantidade * self.get_sinal()

    def __repr__(self) -> str:
        sinal = "+" if self.get_sinal() > 0 else "-"
        return (
            f"<StockMovement id={self.id} "
            f"product_id={self.product_id} "
            f"tipo={self.tipo} "
            f"qty={sinal}{self.quantidade}>"
        )