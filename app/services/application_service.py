from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.repositories.finance_repository import (
    create_expense,
    get_expense,
    list_active_expenses,
    list_expenses,
    list_sales,
    soft_delete_expense,
)
from app.repositories.movement_repository import list_recent_corrections
from app.repositories.product_repository import (
    get_product,
    list_active_products,
    list_products_with_recipe_relationships,
)
from app.services.cost_service import calcular_custo_receita, get_custo_unitario_produto
from app.services.dashboard_service import (
    get_abertos_proximos_vencimento,
    get_dashboard_estoque,
    get_lotes_abertos_detalhados,
    get_produtos_abaixo_minimo,
)
from app.services.movement_services import (
    consumir_lote_completo,
    registrar_abertura,
    registrar_ajuste,
    registrar_consumo,
    registrar_entrada,
    registrar_perda,
)
from app.services.product_service import (
    criar_produto,
    delete_product,
    desativar_produto,
)
from app.services.recipe_service import (
    adicionar_ingrediente_receita,
    atualizar_quantidade_receita,
    criar_receita_item,
    desativar_receita,
    mudar_preco_receita,
    remover_receita,
    remover_receita_item,
)
from app.services.session_scope import session_scope
from app.utils.unit_converter import quantidade_exibicao


def dashboard_estoque() -> list[dict[str, Any]]:
    with session_scope() as session:
        return get_dashboard_estoque(session)


def lotes_abertos_detalhados() -> list[dict[str, Any]]:
    with session_scope() as session:
        return get_lotes_abertos_detalhados(session)


def abertos_proximos_vencimento(dias: int = 3) -> list[dict[str, Any]]:
    with session_scope() as session:
        return get_abertos_proximos_vencimento(session, dias=dias)


def produtos_abaixo_minimo() -> list[dict[str, Any]]:
    with session_scope() as session:
        return get_produtos_abaixo_minimo(session)


def produtos_ativos_opcoes() -> dict[str, int]:
    with session_scope() as session:
        return {p.nome: p.id for p in list_active_products(session)}


def abrir_produto(product_id: int, quantidade: float) -> None:
    with session_scope() as session:
        produto = get_product(session, product_id)
        validade_aberto = None
        if produto and produto.validade_apos_abertura:
            validade_aberto = date.today() + timedelta(
                days=int(produto.validade_apos_abertura)
            )
        registrar_abertura(
            session,
            product_id=product_id,
            quantidade=quantidade,
            data_abertura=date.today(),
            validade_aberto=validade_aberto,
        )


def esgotar_lote(lot_id: int) -> None:
    with session_scope() as session:
        consumir_lote_completo(session, lot_id)


def registrar_consumo_ui(
    product_id: int, quantidade: float, lot_id: int | None, observacao: str | None
) -> None:
    with session_scope() as session:
        registrar_consumo(
            session,
            product_id,
            quantidade,
            date.today(),
            lot_id=lot_id,
            observacao=observacao,
        )


def registrar_perda_ui(
    product_id: int,
    quantidade: float,
    motivo: str,
    estoque_afetado: str,
    lot_id: int | None,
    observacao: str | None,
) -> None:
    with session_scope() as session:
        registrar_perda(
            session,
            product_id,
            quantidade,
            motivo,
            date.today(),
            estoque_afetado=estoque_afetado,
            lot_id=lot_id,
            observacao=observacao,
        )


def registrar_ajuste_ui(
    product_id: int,
    quantidade: float,
    direcao: str,
    motivo: str,
    observacao: str | None = None,
    movimento_referencia_id: int | None = None,
) -> None:
    with session_scope() as session:
        registrar_ajuste(
            session,
            product_id,
            quantidade,
            direcao=direcao,
            motivo=motivo,
            data_ajuste=date.today(),
            observacao=observacao,
            movimento_referencia_id=movimento_referencia_id,
        )


def registrar_compra_ui(
    product_id: int,
    quantidade: float,
    preco_unitario: float,
    data_compra,
    data_validade,
    fornecedor: str,
    tempo_entrega: int,
):
    with session_scope() as session:
        movimento = registrar_entrada(
            session,
            product_id,
            quantidade,
            preco_unitario,
            data_compra,
            data_validade,
            fornecedor,
            tempo_entrega,
        )
        return SimpleNamespace(
            id=movimento.id,
            preco_total=movimento.preco_total,
        )


def catalogo_produtos():
    with session_scope() as session:
        return list_products_with_recipe_relationships(session)


def salvar_produto_com_receita(**kwargs):
    ingredientes = kwargs.pop("ingredientes", [])
    with session_scope() as session:
        try:
            produto = criar_produto(session=session, **kwargs)
            if kwargs.get("tipo_produto") == "receita":
                for item in ingredientes:
                    criar_receita_item(
                        session=session,
                        recipe_id=produto.id,
                        ingredient_id=item["ingredient_id"],
                        quantity=item["quantidade_estoque"],
                    )
            nome = produto.nome
            return nome
        except IntegrityError:
            session.rollback()
            raise ValueError("Já existe um produto com esse nome.")
        except Exception:
            session.rollback()
            raise


def excluir_produto_ui(product_id: int) -> None:
    with session_scope() as session:
        delete_product(session, product_id)


def alternar_produto_ui(product_id: int) -> None:
    with session_scope() as session:
        desativar_produto(session, product_id)


def copiar_ingredientes_receita(receita_id: int) -> list[dict[str, Any]]:
    with session_scope() as session:
        receita = get_product(session, receita_id)
        if not receita:
            raise ValueError("Receita não encontrada.")
        return [
            {
                "ingredient_id": item.ingredient_id,
                "nome": item.ingredient.nome,
                "unidade": item.ingredient.unidade_medida,
                "quantidade_exibicao": quantidade_exibicao(
                    item.quantity, item.ingredient.unidade_medida
                ),
                "quantidade_estoque": item.quantity,
            }
            for item in receita.recipe_items
        ]


def custo_receita_ui(receita):
    with session_scope() as session:
        receita_db = get_product(session, receita.id)
        return calcular_custo_receita(session, receita_db)


def custo_unitario_produto_ui(product_id: int):
    with session_scope() as session:
        return get_custo_unitario_produto(session, product_id)


def mudar_preco_receita_ui(receita_id: int, novo_preco: float) -> None:
    with session_scope() as session:
        mudar_preco_receita(session, receita_id, novo_preco)


def adicionar_ingrediente_receita_ui(
    recipe_id: int, ingredient_id: int, quantity: float
) -> None:
    with session_scope() as session:
        adicionar_ingrediente_receita(session, recipe_id, ingredient_id, quantity)


def remover_receita_item_ui(item_id: int) -> None:
    with session_scope() as session:
        remover_receita_item(session, item_id)


def atualizar_quantidade_receita_ui(item_id: int, quantity: float) -> None:
    with session_scope() as session:
        atualizar_quantidade_receita(session, item_id, quantity)


def remover_receita_ui(receita_id: int) -> None:
    with session_scope() as session:
        remover_receita(session, receita_id)


def alternar_receita_ui(receita_id: int) -> None:
    with session_scope() as session:
        desativar_receita(session, receita_id)


def correcoes_recentes(limit: int = 10) -> list[dict[str, Any]]:
    with session_scope() as session:
        ajustes = list_recent_corrections(session, limit=limit)
        return [
            {
                "direcao": a.direcao,
                "produto": a.product.nome,
                "quantidade": a.quantidade,
                "motivo": a.motivo,
            }
            for a in ajustes
        ]


def dados_dashboard_financeiro() -> dict[str, Any]:
    from app.services.inventory_service import (
        get_lucro_estimado,
        get_total_gastos,
        get_total_investido,
        get_total_receita,
        get_total_vendas,
    )

    with session_scope() as session:
        sales = [
            {"Data": s.data_venda, "Valor": s.valor_total} for s in list_sales(session)
        ]
        expenses_chart = [
            {"Categoria": e.categoria, "Valor": e.valor} for e in list_expenses(session)
        ]
        expenses = [
            {
                "id": e.id,
                "nome": e.nome,
                "categoria": e.categoria,
                "valor": e.valor,
                "data": e.data,
            }
            for e in list_active_expenses(session)
        ]
        return {
            "receita": get_total_receita(session),
            "investimento": get_total_investido(session),
            "gastos": get_total_gastos(session),
            "lucro": get_lucro_estimado(session),
            "vendas": get_total_vendas(session),
            "sales": sales,
            "expenses_chart": expenses_chart,
            "expenses": expenses,
        }


def criar_gasto(nome: str, categoria: str, valor: float, data_gasto) -> None:
    with session_scope() as session:
        create_expense(session, nome, categoria, valor, data_gasto)
        session.commit()


def obter_gasto(expense_id: int) -> dict[str, Any] | None:
    with session_scope() as session:
        expense = get_expense(session, expense_id)
        if not expense:
            return None
        return {"id": expense.id, "nome": expense.nome}


def excluir_gasto(expense_id: int) -> None:
    with session_scope() as session:
        expense = get_expense(session, expense_id)
        if not expense:
            raise ValueError("Gasto não encontrado.")
        soft_delete_expense(session, expense)
        session.commit()


def historico_produto(product_id: int, limit: int = 50):
    from app.services.dashboard_service import get_historico_produto

    with session_scope() as session:
        return get_historico_produto(session, product_id, limit=limit)
