"""Regras de negócio de estoque e dashboard."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from sqlite3 import IntegrityError
from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database.seed import DEFAULT_TENANT_ID
from app.models import Expense, Product, Sale, StockLot, StockMovement
from app.models.enums import ProductType
from app.models.recipes import RecipeItem


def _to_float(value) -> float:
    if value is None:
        return 0.0
    return float(value)


def _get_product(session: Session, product_id: int) -> Product:
    produto = session.get(Product, product_id)
    if not produto:
        raise ValueError("Produto não encontrado.")
    return produto


# ---------------------------------------------------------------------------
# Produtos
# ---------------------------------------------------------------------------


def criar_produto(
    session: Session,
    nome: str,
    tipo_produto: str,
    unidade_medida: str,
    estoque_minimo: float,
    controla_abertura: bool,
    preco_venda: Optional[float] = None,
    validade_apos_abertura: Optional[int] = None,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> Product:

    if tipo_produto not in (
        "materia_prima",
        "consumivel",
        "produto_final",
        "receita",
    ):
        raise ValueError(
            "Tipo de produto inválido."
        )

    if tipo_produto in (
        "produto_final",
        "receita",
    ):
        controla_abertura = False
        validade_apos_abertura = None

    produto = Product(
        tenant_id=tenant_id,
        nome=nome.strip(),
        tipo_produto=tipo_produto,
        unidade_medida=unidade_medida,
        estoque_minimo=estoque_minimo,
        controla_abertura=controla_abertura,
        validade_apos_abertura=validade_apos_abertura,
        preco_venda=preco_venda,
    )

    session.add(produto)
    session.commit()
    session.refresh(produto)

    return produto

def criar_receita_item(
    session: Session,
    recipe_id: int,
    ingredient_id: int,
    quantity: float,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> RecipeItem:
    """
    Adiciona um ingrediente a uma receita.
    """

    if quantity <= 0:
        raise ValueError(
            "A quantidade deve ser maior que zero."
        )

    receita = (
        session.query(Product)
        .filter(
            Product.id == recipe_id,
            Product.tenant_id == tenant_id,
        )
        .first()
    )

    if not receita:
        raise ValueError("Receita não encontrada.")

    if receita.tipo_produto != "receita":
        raise ValueError(
            "O produto informado não é uma receita."
        )

    ingrediente = (
        session.query(Product)
        .filter(
            Product.id == ingredient_id,
            Product.tenant_id == tenant_id,
        )
        .first()
    )

    if not ingrediente:
        raise ValueError("Ingrediente não encontrado.")

    if ingrediente.tipo_produto == "receita":
        raise ValueError(
            "Uma receita não pode ser ingrediente de outra receita."
        )

    existente = (
        session.query(RecipeItem)
        .filter(
            RecipeItem.recipe_id == recipe_id,
            RecipeItem.ingredient_id == ingredient_id,
        )
        .first()
    )

    if existente:
        raise ValueError(
            "Este ingrediente já foi adicionado."
        )

    item = RecipeItem(
        tenant_id=tenant_id,
        recipe_id=recipe_id,
        ingredient_id=ingredient_id,
        quantity=quantity,
    )

    session.add(item)
    session.commit()
    session.refresh(item)

    return item


def buscar_ingredientes_receita(
    session: Session,
    recipe_id: int,
    tenant_id: int = DEFAULT_TENANT_ID,
) -> list[RecipeItem]:
    """
    Retorna todos os ingredientes de uma receita.
    """

    return (
        session.query(RecipeItem)
        .join(
            Product,
            RecipeItem.recipe_id == Product.id,
        )
        .filter(
            RecipeItem.recipe_id == recipe_id,
            Product.tenant_id == tenant_id,
        )
        .all()
    )

# ---------------------------------------------------------------------------
# Lotes em uso
# ---------------------------------------------------------------------------


def get_lotes_abertos(
    session: Session,
    product_id: Optional[int] = None,
) -> list[StockLot]:
    q = (
        session.query(StockLot)
        .filter(StockLot.status == "open")
        .filter(StockLot.quantidade_atual > 1e-9)
        .order_by(
            StockLot.validade.asc().nulls_last(),
            StockLot.data_abertura.asc(),
            StockLot.id.asc(),
        )
    )
    if product_id is not None:
        q = q.filter(StockLot.product_id == product_id)
    return q.all()


def get_estoque_aberto(session: Session, product_id: int) -> float:
    """Saldo em uso = soma dos lotes abertos."""
    result = (
        session.query(func.coalesce(func.sum(StockLot.quantidade_atual), 0))
        .filter(StockLot.product_id == product_id)
        .filter(StockLot.status == "open")
        .scalar()
    )
    return _to_float(result)


def get_estoque_fechado(session: Session, product_id: int) -> float:
    """Estoque fechado via ledger (perda só conta se estoque_afetado=fechado)."""
    result = (
        session.query(
            func.coalesce(
                func.sum(
                    case(
                        (
                            StockMovement.tipo.in_(["entrada", "estorno"]),
                            StockMovement.quantidade,
                        ),
                        (StockMovement.tipo == "abertura", -StockMovement.quantidade),
                        (
                            (StockMovement.tipo == "perda")
                            & (StockMovement.estoque_afetado == "fechado"),
                            -StockMovement.quantidade,
                        ),
                        (
                            StockMovement.tipo == "ajuste",
                            case(
                                (
                                    StockMovement.direcao == "entrada",
                                    StockMovement.quantidade,
                                ),
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
        .filter(StockMovement.tipo != "consumo")
        .scalar()
    )
    return _to_float(result)


def get_estoque_total(session: Session, product_id: int) -> float:
    return get_estoque_fechado(session, product_id) + get_estoque_aberto(
        session, product_id
    )


def get_dashboard_estoque(session: Session) -> list[dict]:
    produtos = (
    session.query(Product)
    .filter(
        Product.ativo.is_(True),
        Product.tipo_produto.in_(
            [
                ProductType.MATERIA_PRIMA,
                ProductType.CONSUMIVEL,
                ProductType.PRODUTO_FINAL,
            ]
        ),
    )
    .all()
)
    resultado = []

    for p in produtos:
        fechado = get_estoque_fechado(session, p.id)
        aberto = get_estoque_aberto(session, p.id) if p.controla_abertura else 0.0
        total = fechado + aberto

        resultado.append({
            "id": p.id,
            "nome": p.nome,
            "tipo": p.tipo_produto.value,
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
    return [p for p in get_dashboard_estoque(session) if p["abaixo_minimo"]]


def get_abertos_proximos_vencimento(session: Session, dias: int = 3) -> list[dict]:
    """Lotes abertos com validade nos próximos N dias."""
    hoje = date.today()
    limite = hoje + timedelta(days=dias)

    lotes = (
        session.query(StockLot)
        .filter(StockLot.status == "open")
        .filter(StockLot.quantidade_atual > 1e-9)
        .filter(StockLot.validade.isnot(None))
        .filter(StockLot.validade <= limite)
        .filter(StockLot.validade >= hoje)
        .order_by(StockLot.validade.asc())
        .all()
    )

    return [
        {
            "lot_id": lot.id,
            "produto": lot.product.nome,
            "quantidade": lot.quantidade_atual,
            "validade": lot.validade,
            "dias_restantes": (lot.validade - hoje).days,
        }
        for lot in lotes
    ]


def get_lotes_abertos_detalhados(session: Session) -> list[dict]:
    """Lista lotes abertos para exibição na UI."""
    lotes = get_lotes_abertos(session)
    return [
        {
            "lot_id": lot.id,
            "product_id": lot.product_id,
            "produto": lot.product.nome,
            "quantidade_atual": lot.quantidade_atual,
            "validade": lot.validade,
            "data_abertura": lot.data_abertura,
            "dias_restantes": (
                (lot.validade - date.today()).days if lot.validade else None
            ),
        }
        for lot in lotes
    ]


def _consumir_de_lotes(
    session: Session,
    product_id: int,
    quantidade: float,
    tipo: str,
    data_movimento: date,
    motivo: Optional[str] = None,
    observacao: Optional[str] = None,
) -> list[StockMovement]:
    """Consome/perde de lotes em FEFO; retorna movimentos gerados."""
    produto = _get_product(session, product_id)
    lotes = get_lotes_abertos(session, product_id)
    saldo_lotes = sum(l.quantidade_atual for l in lotes)

    if saldo_lotes < quantidade:
        raise ValueError(
            f"Estoque aberto insuficiente: disponível {saldo_lotes}, "
            f"solicitado {quantidade}"
        )

    restante = quantidade
    movimentos: list[StockMovement] = []

    for lot in lotes:
        if restante <= 0:
            break

        qtd = min(lot.quantidade_atual, restante)
        lot.quantidade_atual = round(lot.quantidade_atual - qtd, 6)
        if lot.quantidade_atual <= 1e-9:
            lot.quantidade_atual = 0
            lot.status = "closed"

        mov = StockMovement(
            tenant_id=produto.tenant_id,
            product_id=product_id,
            lot_id=lot.id,
            tipo=tipo,
            quantidade=qtd,
            estoque_afetado="aberto",
            motivo=motivo,
            data_movimento=data_movimento,
            observacao=observacao,
        )
        session.add(mov)
        movimentos.append(mov)
        restante -= qtd

    return movimentos


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
    produto = _get_product(session, product_id)
    pu = Decimal(str(preco_unitario))
    pt = Decimal(str(quantidade)) * pu

    mov = StockMovement(
        tenant_id=produto.tenant_id,
        product_id=product_id,
        tipo="entrada",
        quantidade=quantidade,
        preco_unitario=pu,
        preco_total=pt,
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
    movimento_referencia_id: Optional[int] = None,
    observacao: Optional[str] = None,
) -> StockMovement:
    produto = _get_product(session, product_id)
    estoque_atual = get_estoque_fechado(session, product_id)
    if estoque_atual < quantidade:
        raise ValueError(
            f"Estoque fechado insuficiente: disponível {estoque_atual}, "
            f"solicitado {quantidade}"
        )

    mov = StockMovement(
        tenant_id=produto.tenant_id,
        product_id=product_id,
        tipo="abertura",
        quantidade=quantidade,
        validade_aberto=validade_aberto,
        movimento_referencia_id=movimento_referencia_id,
        data_movimento=data_abertura,
        observacao=observacao,
    )
    session.add(mov)
    session.flush()

    lot = StockLot(
        tenant_id=produto.tenant_id,
        product_id=product_id,
        abertura_movement_id=mov.id,
        quantidade_inicial=quantidade,
        quantidade_atual=quantidade,
        data_abertura=data_abertura,
        validade=validade_aberto,
        status="open",
    )
    session.add(lot)

    session.commit()
    session.expire_all()
    session.refresh(mov)
    return mov


def registrar_consumo(
    session: Session,
    product_id: int,
    quantidade: float,
    data_consumo: date,
    lot_id: Optional[int] = None,
    observacao: Optional[str] = None,
) -> list[StockMovement]:
    """Registra consumo; aloca em lote específico ou FEFO."""
    if lot_id is not None:
        lot = session.get(StockLot, lot_id)
        if not lot or lot.product_id != product_id or lot.status != "open":
            raise ValueError("Lote inválido ou indisponível.")
        if lot.quantidade_atual < quantidade:
            raise ValueError(
                f"Saldo do lote insuficiente: {lot.quantidade_atual}, "
                f"solicitado {quantidade}"
            )
        produto = _get_product(session, product_id)
        lot.quantidade_atual = round(lot.quantidade_atual - quantidade, 6)
        if lot.quantidade_atual <= 1e-9:
            lot.quantidade_atual = 0
            lot.status = "closed"
        mov = StockMovement(
            tenant_id=produto.tenant_id,
            product_id=product_id,
            lot_id=lot.id,
            tipo="consumo",
            quantidade=quantidade,
            estoque_afetado="aberto",
            data_movimento=data_consumo,
            observacao=observacao,
        )
        session.add(mov)
        session.commit()
        session.expire_all()
        session.refresh(mov)
        return [mov]

    movimentos = _consumir_de_lotes(
        session,
        product_id,
        quantidade,
        tipo="consumo",
        data_movimento=data_consumo,
        observacao=observacao,
    )
    session.commit()
    session.expire_all()
    for m in movimentos:
        session.refresh(m)
    return movimentos


def consumir_lote_completo(
    session: Session,
    lot_id: int,
    data_consumo: Optional[date] = None,
    observacao: Optional[str] = None,
) -> list[StockMovement]:
    """Consome 100% do saldo de um lote (atalho na UI)."""
    lot = session.get(StockLot, lot_id)
    if not lot or lot.status != "open" or lot.quantidade_atual <= 1e-9:
        raise ValueError("Lote inválido ou já encerrado.")
    return registrar_consumo(
        session,
        lot.product_id,
        lot.quantidade_atual,
        data_consumo or date.today(),
        lot_id=lot.id,
        observacao=observacao,
    )


def registrar_perda(
    session: Session,
    product_id: int,
    quantidade: float,
    motivo: str,
    data_perda: date,
    estoque_afetado: str = "fechado",
    lot_id: Optional[int] = None,
    observacao: Optional[str] = None,
) -> StockMovement | list[StockMovement]:
    if not motivo or not motivo.strip():
        raise ValueError("Motivo é obrigatório para registro de perda.")

    if estoque_afetado not in ("fechado", "aberto"):
        raise ValueError("estoque_afetado deve ser 'fechado' ou 'aberto'.")

    if estoque_afetado == "aberto":
        if lot_id is not None:
            produto = _get_product(session, product_id)
            lot = session.get(StockLot, lot_id)
            if not lot or lot.product_id != product_id or lot.status != "open":
                raise ValueError("Lote inválido ou indisponível.")
            if lot.quantidade_atual < quantidade:
                raise ValueError(
                    f"Saldo do lote insuficiente: {lot.quantidade_atual}, "
                    f"solicitado {quantidade}"
                )
            lot.quantidade_atual -= quantidade
            if lot.quantidade_atual <= 0:
                lot.quantidade_atual = 0
                lot.status = "closed"
            mov = StockMovement(
                tenant_id=produto.tenant_id,
                product_id=product_id,
                lot_id=lot.id,
                tipo="perda",
                quantidade=quantidade,
                estoque_afetado="aberto",
                motivo=motivo.strip(),
                data_movimento=data_perda,
                observacao=observacao,
            )
            session.add(mov)
            session.commit()
            session.refresh(mov)
            return mov

        movimentos = _consumir_de_lotes(
            session,
            product_id,
            quantidade,
            tipo="perda",
            data_movimento=data_perda,
            motivo=motivo.strip(),
            observacao=observacao,
        )
        session.commit()
        return movimentos

    produto = _get_product(session, product_id)
    fechado = get_estoque_fechado(session, product_id)
    if fechado < quantidade:
        raise ValueError(
            f"Estoque fechado insuficiente: disponível {fechado}, "
            f"solicitado {quantidade}"
        )

    mov = StockMovement(
        tenant_id=produto.tenant_id,
        product_id=product_id,
        tipo="perda",
        quantidade=quantidade,
        estoque_afetado="fechado",
        motivo=motivo.strip(),
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
    direcao: str,
    motivo: str,
    data_ajuste: date,
    observacao: Optional[str] = None,
    movimento_referencia_id: Optional[int] = None,
) -> StockMovement:
    if direcao not in ("entrada", "saida"):
        raise ValueError("Direção deve ser 'entrada' ou 'saida'.")
    if quantidade <= 0:
        raise ValueError("Quantidade deve ser maior que zero.")
    if not motivo or not motivo.strip():
        raise ValueError("Motivo é obrigatório para ajuste.")

    produto = _get_product(session, product_id)
    preco_unitario = Decimal("0")

    if movimento_referencia_id:
        movimento_original = session.get(StockMovement, movimento_referencia_id)
        if movimento_original and movimento_original.preco_unitario is not None:
            preco_unitario = Decimal(str(movimento_original.preco_unitario))

    if preco_unitario == 0:
        cm = get_custo_medio(session, product_id)
        if cm:
            preco_unitario = Decimal(str(cm))

    mov = StockMovement(
        tenant_id=produto.tenant_id,
        product_id=product_id,
        tipo="ajuste",
        direcao=direcao,
        quantidade=quantidade,
        preco_unitario=preco_unitario,
        motivo=motivo.strip(),
        observacao=observacao,
        data_movimento=data_ajuste,
        movimento_referencia_id=movimento_referencia_id,
    )
    session.add(mov)
    session.commit()
    session.refresh(mov)
    return mov


def registrar_estorno(
    session: Session,
    movimento_id: int,
    observacao: Optional[str] = None,
) -> StockMovement:
    """Estorna uma movimentação anterior (auditoria)."""
    original = session.get(StockMovement, movimento_id)
    if not original:
        raise ValueError("Movimentação não encontrada.")
    if original.tipo == "estorno":
        raise ValueError("Não é possível estornar um estorno.")

    produto = _get_product(session, original.product_id)

    mov = StockMovement(
        tenant_id=produto.tenant_id,
        product_id=original.product_id,
        tipo="estorno",
        quantidade=original.quantidade,
        movimento_referencia_id=original.id,
        data_movimento=date.today(),
        observacao=observacao or f"Estorno da movimentação #{original.id}",
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
    movs = (
        session.query(StockMovement)
        .filter(StockMovement.product_id == product_id)
        .order_by(
            StockMovement.data_movimento.desc(),
            StockMovement.id.desc(),
        )
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
            "preco_unitario": _to_float(m.preco_unitario),
            "motivo": m.motivo,
            "observacao": m.observacao,
            "movimento_referencia_id": m.movimento_referencia_id,
            "lot_id": m.lot_id,
            "estoque_afetado": m.estoque_afetado,
        }
        for m in movs
    ]


def get_custo_medio(session: Session, product_id: int) -> Optional[float]:
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

    return _to_float(total_custo) / _to_float(total_qty)


def get_valor_estoque_total(session: Session) -> float:
    produtos = session.query(Product).all()
    total = 0.0

    for p in produtos:
        qty = get_estoque_total(session, p.id)
        custo = get_custo_medio(session, p.id)
        if qty > 0 and custo:
            total += qty * custo

    return total


# ---------------------------------------------------------------------------
# Dashboard financeiro
# ---------------------------------------------------------------------------


def get_total_receita(db) -> float:
    return _to_float(db.query(func.sum(Sale.valor_total)).scalar())


def get_total_investido(db) -> float:
    total = db.query(
        func.sum(
            case(
                (
                    StockMovement.tipo.in_(["entrada", "estorno"]),
                    StockMovement.quantidade * StockMovement.preco_unitario,
                ),
                (
                    (StockMovement.tipo == "ajuste")
                    & (StockMovement.direcao == "saida"),
                    -(StockMovement.quantidade * StockMovement.preco_unitario),
                ),
                (
                    (StockMovement.tipo == "ajuste")
                    & (StockMovement.direcao == "entrada"),
                    StockMovement.quantidade * StockMovement.preco_unitario,
                ),
                else_=0,
            )
        )
    ).scalar()
    return _to_float(total)


def get_total_gastos(db) -> float:
    return _to_float(db.query(func.sum(Expense.valor)).scalar())


def get_total_vendas(db) -> int:
    return int(db.query(func.count(Sale.id)).scalar() or 0)


def get_lucro_estimado(db) -> float:
    return get_total_receita(db) - get_total_investido(db) - get_total_gastos(db)


# ---------------------------------------------------------------------------
# desativar / atualizar
# ---------------------------------------------------------------------------


def mudar_preco_receita(
    session: Session,
    receita_id: int,
    novo_preco: float,
) -> Product:

    if novo_preco <= 0:
        raise ValueError(
            "O preço deve ser maior que zero."
        )

    receita = (
        session.query(Product)
        .filter(Product.id == receita_id)
        .first()
    )

    if not receita:
        raise ValueError(
            "Receita não encontrada."
        )

    if receita.tipo_produto.value != "receita":
        raise ValueError(
            "O produto informado não é uma receita."
        )

    receita.preco_venda = novo_preco

    session.commit()
    session.refresh(receita)

    return receita
    



def pode_excluir(produto) -> bool:
    return (
        not produto.movements
        and not produto.lots
        and not produto.recipe_items
        and not produto.ingredient_in_recipes
    )

def desativar_produto(session: Session, product_id: int) -> Product:
    produto = _get_product(session, product_id)
    produto.ativo = not produto.ativo
    session.commit()
    session.refresh(produto)
    return produto


def delete_product(
    session: Session,
    product_id: int,
) -> None:
    try:
        produto = _get_product(session, product_id)

        if produto.movements:
            raise ValueError(
                "Este produto possui movimentações registradas."
            )

        if produto.lots:
            raise ValueError(
                "Este produto possui lotes vinculados."
            )

        # Produto é uma receita
        if produto.recipe_items:
            raise ValueError(
                "Esta receita possui ingredientes cadastrados."
            )

        # Produto é usado como ingrediente
        if produto.ingredient_in_recipes:
            raise ValueError(
                "Este produto é utilizado em uma ou mais receitas."
            )

        session.delete(produto)
        session.commit()

    except IntegrityError:
        session.rollback()

        raise ValueError(
            "Não foi possível excluir o produto porque existem registros relacionados a ele."
        )
    
def pode_excluir_receita(receita):
    return (
        not receita.sales
        and not receita.movements
    )

def desativar_receita(session: Session, product_id: int) -> Product:
    produto = _get_product(session, product_id)
    produto.ativo = not produto.ativo
    session.commit()
    session.refresh(produto)
    return produto

def remover_receita(session: Session, receita_id: int) -> None:
    try: 
        receita = _get_product(session, receita_id)

        if receita.tipo_produto != "receita":
            raise ValueError("Produto informado não é uma receita.")

        session.delete(receita)
        session.commit()

    except IntegrityError:
        session.rollback()

        raise ValueError(
            "Não foi possível excluir o produto porque existem registros relacionados a ele."
        )

def remover_receita_item(
    session: Session,
    ingredient_id: int,
) -> None:

    item = (
        session.query(RecipeItem)
        .filter(
            RecipeItem.ingredient_id == ingredient_id
        )
        .first()
    )

    if not item:
        raise ValueError(
            "Ingrediente não encontrado."
        )

    session.delete(item)
    session.commit()

def atualizar_quantidade_receita(
    session: Session,
    recipe_item_id: int,
    quantity: float,
) -> RecipeItem:

    item = (
        session.query(RecipeItem)
        .filter(
            RecipeItem.id == recipe_item_id
        )
        .first()
    )

    if not item:
        raise ValueError(
            "Item da receita não encontrado."
        )

    item.quantity = quantity

    session.commit()
    session.refresh(item)

    return item

def adicionar_ingrediente_receita(
    session: Session,
    recipe_id: int,
    ingredient_id: int,
    quantity: float,
) -> RecipeItem:

    if quantity <= 0:
        raise ValueError(
            "Quantidade deve ser maior que zero."
        )

    existe = (
        session.query(RecipeItem)
        .filter(
            RecipeItem.recipe_id == recipe_id,
            RecipeItem.ingredient_id == ingredient_id,
        )
        .first()
    )

    if existe:
        raise ValueError(
            "Ingrediente já existe na receita."
        )

    item = RecipeItem(
        tenant_id=_get_product(
            session,
            recipe_id,
        ).tenant_id,
        recipe_id=recipe_id,
        ingredient_id=ingredient_id,
        quantity=quantity,
    )

    session.add(item)
    session.commit()
    session.refresh(item)

    return item