"""Regras de negócio de estoque e dashboard.

Camada de service concentra regras para não acoplar
lógica de negócio na interface (Streamlit pages).
"""

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.models import Product, OpenedProduct, Purchase, product, StockMovement





def get_estoque_fechado(session: Session, product_id: int) -> float:
    """
    Estoque fechado = unidades compradas e ainda não abertas.
 
    Cálculo:
        SUM(entradas + estornos) - SUM(aberturas + perdas de fechado)
    """
    result = (
        session.query(
            func.coalesce(
                func.sum(
                    case(
                        (StockMovement.tipo.in_(["entrada", "estorno"]), StockMovement.quantidade),
                        (StockMovement.tipo.in_(["abertura", "perda"]), -StockMovement.quantidade),
                        (
                            (StockMovement.tipo == "ajuste"),
                            case(
                                (StockMovement.direcao == "entrada", StockMovement.quantidade),
                                else_=-StockMovement.quantidade,
                            ),
                        ),
                        else_=0,
                    )
                ),
                0,
            )
        )
        .filter(StockMovement.product_id == product_id)
        .filter(StockMovement.tipo != "consumo")  # consumo só afeta aberto
        .scalar()
    )
    return float(result)


def get_estoque_aberto(session: Session, product_id: int) -> float:
    """
    Estoque em uso = unidades abertas mas ainda não totalmente consumidas.
 
    Cálculo:
        SUM(aberturas) - SUM(consumos)
    """
    result = (
        session.query(
            func.coalesce(
                func.sum(
                    case(
                        (StockMovement.tipo == "abertura", StockMovement.quantidade),
                        (StockMovement.tipo == "consumo", -StockMovement.quantidade),
                        else_=0,
                    )
                ),
                0,
            )
        )
        .filter(StockMovement.product_id == product_id)
        .scalar()
    )
    return float(result)

def get_estoque_total(session: Session, product_id: int) -> float:
    """Estoque total = fechado + aberto."""
    return get_estoque_fechado(session, product_id) + get_estoque_aberto(session, product_id)


def get_dashboard_estoque(session: Session) -> list[dict]:
    """
    Retorna estoque atual de todos os produtos para o dashboard.
    Uma query por produto é aceitável para MVP; otimizar com subquery quando > 500 produtos.
    """
    produtos = session.query(Product).all()
    resultado = []
 
    for p in produtos:
        fechado = get_estoque_fechado(session, p.id)
        aberto = get_estoque_aberto(session, p.id) if p.controla_abertura else 0
        total = fechado + aberto
 
        resultado.append({
            "id": p.id,
            "nome": p.nome,
            "categoria": p.categoria,
            "unidade_medida": p.unidade_medida,
            "estoque_minimo": p.estoque_minimo,
            "estoque_fechado": fechado,
            "estoque_aberto": aberto,
            "estoque_total": total,
            "abaixo_minimo": total < p.estoque_minimo,
            "controla_abertura": p.controla_abertura,
        })
 
    return resultado
 
 
def get_produtos_abaixo_minimo(session: Session) -> list[dict]:
    """Retorna apenas produtos com estoque abaixo do mínimo. Útil para alertas."""
    return [p for p in get_dashboard_estoque(session) if p["abaixo_minimo"]]
 
 
def get_abertos_proximos_vencimento(session: Session, dias: int = 3) -> list[dict]:
    """
    Retorna aberturas cuja validade_aberto vence nos próximos N dias.
    Útil para alertas de desperdício.
    """
    limite = date.today() + timedelta(days=dias)
 
    movs = (
        session.query(StockMovement)
        .filter(StockMovement.tipo == "abertura")
        .filter(StockMovement.validade_aberto != None)
        .filter(StockMovement.validade_aberto <= limite)
        .filter(StockMovement.validade_aberto >= date.today())
        .all()
    )
 
    return [
        {
            "produto": m.product.nome,
            "quantidade": m.quantidade,
            "validade_aberto": m.validade_aberto,
            "dias_restantes": (m.validade_aberto - date.today()).days,
        }
        for m in movs
    ]
 
 
# ---------------------------------------------------------------------------
# Registro de movimentações
# ---------------------------------------------------------------------------
 
def registrar_entrada(
    session: Session,
    product_id: int,
    quantidade: float,
    preco_unitario: float,
    data_compra: date,
    data_validade: Optional[date] = None,
    fornecedor: Optional[str] = None,
    tempo_entrega: Optional[int] = None,
    observacao: Optional[str] = None,
) -> StockMovement:
    """Registra uma compra (entrada de estoque)."""
    mov = StockMovement(
        product_id=product_id,
        tipo="entrada",
        quantidade=quantidade,
        preco_unitario=preco_unitario,
        preco_total=quantidade * preco_unitario,
        data_validade=data_validade,
        fornecedor=fornecedor,
        tempo_entrega=tempo_entrega,
        data_movimento=data_compra,
        observacao=observacao,
    )
    session.add(mov)
    session.commit()
    session.refresh(mov)
    return mov
 
 
def registrar_abertura(
    session: Session,
    product_id: int,
    quantidade: float,
    data_abertura: date,
    validade_aberto: Optional[date] = None,
    entrada_origem_id: Optional[int] = None,
    observacao: Optional[str] = None,
) -> StockMovement:
    """
    Registra abertura de uma unidade.
    Valida se há estoque fechado suficiente antes de abrir.
    """
    estoque_atual = get_estoque_fechado(session, product_id)
    if estoque_atual < quantidade:
        raise ValueError(
            f"Estoque fechado insuficiente: disponível {estoque_atual}, "
            f"solicitado {quantidade}"
        )
 
    mov = StockMovement(
        product_id=product_id,
        tipo="abertura",
        quantidade=quantidade,
        validade_aberto=validade_aberto,
        entrada_origem_id=entrada_origem_id,
        data_movimento=data_abertura,
        observacao=observacao,
    )
    session.add(mov)
    session.commit()
    session.refresh(mov)
    return mov
 
 
def registrar_consumo(
    session: Session,
    product_id: int,
    quantidade: float,
    data_consumo: date,
    observacao: Optional[str] = None,
) -> StockMovement:
    """Registra consumo de produto aberto."""
    aberto = get_estoque_aberto(session, product_id)
    if aberto < quantidade:
        raise ValueError(
            f"Estoque aberto insuficiente: disponível {aberto}, "
            f"solicitado {quantidade}"
        )
 
    mov = StockMovement(
        product_id=product_id,
        tipo="consumo",
        quantidade=quantidade,
        data_movimento=data_consumo,
        observacao=observacao,
    )
    session.add(mov)
    session.commit()
    session.refresh(mov)
    return mov
 
 
def registrar_perda(
    session: Session,
    product_id: int,
    quantidade: float,
    motivo: str,
    data_perda: date,
    observacao: Optional[str] = None,
) -> StockMovement:
    """Registra perda (vencimento, dano, furto). Motivo é obrigatório."""
    if not motivo or not motivo.strip():
        raise ValueError("Motivo é obrigatório para registro de perda.")
 
    mov = StockMovement(
        product_id=product_id,
        tipo="perda",
        quantidade=quantidade,
        motivo=motivo,
        data_movimento=data_perda,
        observacao=observacao,
    )
    session.add(mov)
    session.commit()
    session.refresh(mov)
    return mov
 
 
def registrar_ajuste(
    session: Session,
    product_id: int,
    quantidade: float,
    direcao: str,  # "entrada" ou "saida"
    motivo: str,
    data_ajuste: date,
    observacao: Optional[str] = None,
) -> StockMovement:
    """
    Ajuste manual de estoque. Motivo e direção são obrigatórios.
    Use para corrigir diferenças encontradas em inventário físico.
    """
    if direcao not in ("entrada", "saida"):
        raise ValueError("Direção deve ser 'entrada' ou 'saida'.")
    if not motivo or not motivo.strip():
        raise ValueError("Motivo é obrigatório para ajuste.")
 
    mov = StockMovement(
        product_id=product_id,
        tipo="ajuste",
        quantidade=quantidade,
        direcao=direcao,
        motivo=motivo,
        data_movimento=data_ajuste,
        observacao=observacao,
    )
    session.add(mov)
    session.commit()
    session.refresh(mov)
    return mov
 
 
# ---------------------------------------------------------------------------
# Histórico e analytics
# ---------------------------------------------------------------------------
 
def get_historico_produto(
    session: Session,
    product_id: int,
    limit: int = 50,
) -> list[dict]:
    """Últimas N movimentações de um produto, ordenadas por data."""
    movs = (
        session.query(StockMovement)
        .filter(StockMovement.product_id == product_id)
        .order_by(StockMovement.data_movimento.desc(), StockMovement.id.desc())
        .limit(limit)
        .all()
    )
 
    return [
        {
            "id": m.id,
            "data": m.data_movimento,
            "tipo": m.tipo,
            "quantidade": m.get_quantidade_efetiva(),
            "fornecedor": m.fornecedor,
            "preco_unitario": m.preco_unitario,
            "motivo": m.motivo,
            "observacao": m.observacao,
        }
        for m in movs
    ]
 
 
def get_custo_medio(session: Session, product_id: int) -> Optional[float]:
    """
    Custo médio ponderado das entradas.
    Útil para calcular valor do estoque e margem futura.
    """
    result = (
        session.query(
            func.sum(StockMovement.preco_total),
            func.sum(StockMovement.quantidade),
        )
        .filter(StockMovement.product_id == product_id)
        .filter(StockMovement.tipo == "entrada")
        .one()
    )
 
    total_custo, total_qty = result
    if not total_qty or total_qty == 0:
        return None
 
    return total_custo / total_qty
 
 
def get_valor_estoque_total(session: Session) -> float:
    """
    Valor total do estoque = SUM(estoque_atual * custo_medio) por produto.
    Útil para o dashboard financeiro.
    """
    produtos = session.query(Product).all()
    total = 0.0
 
    for p in produtos:
        qty = get_estoque_total(session, p.id)
        custo = get_custo_medio(session, p.id)
        if qty > 0 and custo:
            total += qty * custo
 
    return total








