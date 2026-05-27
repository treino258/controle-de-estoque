"""Testes do inventory_service.

Execute com:
    pytest tests/test_inventory_service.py -v

Por que testar o service e não as páginas Streamlit?
- O service é puro Python — sem dependência de UI
- Estes testes vão funcionar quando você migrar para FastAPI
- Cobrem a lógica mais crítica: cálculo de estoque
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.services import inventory_service as svc

# Banco em memória para testes — nunca toca o banco real
@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        yield s


@pytest.fixture
def produto(session):
    p = Product(
        nome="Café",
        categoria="Bebidas",
        unidade_medida="kg",
        estoque_minimo=2.0,
        controla_abertura=True,
        validade_apos_abertura=30,
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


# ---------------------------------------------------------------------------
# Testes de cálculo de estoque
# ---------------------------------------------------------------------------

class TestEstoqueFechado:

    def test_sem_movimentacoes_retorna_zero(self, session, produto):
        assert svc.get_estoque_fechado(session, produto.id) == 0.0

    def test_entrada_aumenta_estoque(self, session, produto):
        svc.registrar_entrada(session, produto.id, 10.0, 25.0, date.today())
        assert svc.get_estoque_fechado(session, produto.id) == 10.0

    def test_multiplas_entradas_somam(self, session, produto):
        svc.registrar_entrada(session, produto.id, 5.0, 25.0, date.today())
        svc.registrar_entrada(session, produto.id, 3.0, 26.0, date.today())
        assert svc.get_estoque_fechado(session, produto.id) == 8.0

    def test_abertura_subtrai_do_fechado(self, session, produto):
        svc.registrar_entrada(session, produto.id, 10.0, 25.0, date.today())
        svc.registrar_abertura(session, produto.id, 1.0, date.today())
        assert svc.get_estoque_fechado(session, produto.id) == 9.0

    def test_perda_subtrai_do_fechado(self, session, produto):
        svc.registrar_entrada(session, produto.id, 10.0, 25.0, date.today())
        svc.registrar_perda(session, produto.id, 2.0, "Vencimento", date.today())
        assert svc.get_estoque_fechado(session, produto.id) == 8.0

    def test_ajuste_entrada_aumenta(self, session, produto):
        svc.registrar_entrada(session, produto.id, 10.0, 25.0, date.today())
        svc.registrar_ajuste(session, produto.id, 2.0, "entrada", "Inventário físico", date.today())
        assert svc.get_estoque_fechado(session, produto.id) == 12.0

    def test_ajuste_saida_diminui(self, session, produto):
        svc.registrar_entrada(session, produto.id, 10.0, 25.0, date.today())
        svc.registrar_ajuste(session, produto.id, 2.0, "saida", "Diferença de inventário", date.today())
        assert svc.get_estoque_fechado(session, produto.id) == 8.0


class TestEstoqueAberto:

    def test_abertura_aparece_no_aberto(self, session, produto):
        svc.registrar_entrada(session, produto.id, 10.0, 25.0, date.today())
        svc.registrar_abertura(session, produto.id, 1.0, date.today())
        assert svc.get_estoque_aberto(session, produto.id) == 1.0

    def test_consumo_subtrai_do_aberto(self, session, produto):
        svc.registrar_entrada(session, produto.id, 10.0, 25.0, date.today())
        svc.registrar_abertura(session, produto.id, 1.0, date.today())
        svc.registrar_consumo(session, produto.id, 0.5, date.today())
        assert svc.get_estoque_aberto(session, produto.id) == 0.5


class TestValidacoes:

    def test_abertura_sem_estoque_levanta_erro(self, session, produto):
        with pytest.raises(ValueError, match="insuficiente"):
            svc.registrar_abertura(session, produto.id, 1.0, date.today())

    def test_consumo_sem_estoque_aberto_levanta_erro(self, session, produto):
        with pytest.raises(ValueError, match="insuficiente"):
            svc.registrar_consumo(session, produto.id, 1.0, date.today())

    def test_perda_sem_motivo_levanta_erro(self, session, produto):
        svc.registrar_entrada(session, produto.id, 5.0, 25.0, date.today())
        with pytest.raises(ValueError, match="Motivo"):
            svc.registrar_perda(session, produto.id, 1.0, "", date.today())

    def test_ajuste_direcao_invalida_levanta_erro(self, session, produto):
        with pytest.raises(ValueError, match="Direção"):
            svc.registrar_ajuste(session, produto.id, 1.0, "invalido", "teste", date.today())


class TestAlertas:

    def test_produto_abaixo_minimo_aparece_no_alerta(self, session, produto):
        # estoque_minimo = 2.0, não tem nenhuma entrada
        alertas = svc.get_produtos_abaixo_minimo(session)
        assert any(a["id"] == produto.id for a in alertas)

    def test_produto_acima_minimo_nao_aparece_no_alerta(self, session, produto):
        svc.registrar_entrada(session, produto.id, 10.0, 25.0, date.today())
        alertas = svc.get_produtos_abaixo_minimo(session)
        assert not any(a["id"] == produto.id for a in alertas)

    def test_proximos_vencimento(self, session, produto):
        svc.registrar_entrada(session, produto.id, 5.0, 25.0, date.today())
        vence_amanha = date.today() + timedelta(days=1)
        svc.registrar_abertura(
            session, produto.id, 1.0, date.today(), validade_aberto=vence_amanha
        )
        proximos = svc.get_abertos_proximos_vencimento(session, dias=3)
        assert len(proximos) == 1
        assert proximos[0]["dias_restantes"] == 1


class TestCustos:

    def test_custo_medio_com_uma_entrada(self, session, produto):
        svc.registrar_entrada(session, produto.id, 10.0, 25.0, date.today())
        assert svc.get_custo_medio(session, produto.id) == 25.0

    def test_custo_medio_ponderado(self, session, produto):
        # 10kg a R$20 + 10kg a R$30 = custo médio R$25
        svc.registrar_entrada(session, produto.id, 10.0, 20.0, date.today())
        svc.registrar_entrada(session, produto.id, 10.0, 30.0, date.today())
        assert svc.get_custo_medio(session, produto.id) == 25.0

    def test_custo_medio_sem_entradas_retorna_none(self, session, produto):
        assert svc.get_custo_medio(session, produto.id) is None