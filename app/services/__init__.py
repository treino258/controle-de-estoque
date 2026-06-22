from app.services.product_service import (
    _get_product,
    criar_produto,
    desativar_produto,
    delete_product,
    pode_excluir
    )
from app.services.stock_service import (
    get_estoque_total,
    get_lotes_abertos,
    get_estoque_aberto,
    get_estoque_fechado,
    _consumir_de_lotes
    )
from app.services.dashboard_service import (
    get_dashboard_estoque,
    get_produtos_abaixo_minimo,
    get_abertos_proximos_vencimento,
    get_lotes_abertos_detalhados,
    get_historico_produto,
    get_custo_medio,
    get_valor_estoque_total,
    get_total_receita,
    get_total_investido,
    get_total_gastos,
    get_total_vendas,
    get_lucro_estimado,
    )
from app.services.recipe_service import (
    criar_receita_item,
    desativar_receita,
    remover_receita,
    remover_receita_item,
    atualizar_quantidade_receita,
    buscar_ingredientes_receita,
    mudar_preco_receita,
    pode_excluir_receita,
    adicionar_ingrediente_receita,
    obter_receitas_ativas
    )

from app.services.movement_services import (
    registrar_abertura,
    registrar_consumo,
    registrar_ajuste,
    registrar_entrada,
    consumir_lote_completo,
    registrar_perda,
    registrar_estorno,
    )

from app.services.cost_service import (
    calcular_custo_receita,
    get_custo_unitario_receita
    )
