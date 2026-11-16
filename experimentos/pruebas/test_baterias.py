"""Pruebas del caso de la planta de baterías: las instancias armadas coinciden con las tablas del conjunto, las variantes conservan la composición por
familia, el decodificador de C++ coincide con uno independiente en Python en los cuatro modos, el comprobador rechaza calendarios inválidos, CP-SAT
(con y sin pista) devuelve calendarios que lo pasan y ninguna corrida queda bajo las cotas."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jsp_ag.conjunto_bat import AJUSTE, EVALUACION  # noqa: E402
from jsp_ag.hfs import JSON, ProblemaHFS, cargar_baterias, comprobar, cota_capacidad, decodificar_py, instancia_bat  # noqa: E402

pytestmark = pytest.mark.skipif(not JSON.exists(), reason="falta instancias/baterias_parametros.json")


@pytest.fixture(scope="module")
def inst():
    return cargar_baterias()


def test_tamanos_y_familias(inst):
    # operaciones reales de las rutas (el documento da estimaciones menores: 85, 172, 258, 344 y 430)
    assert {k: v.n_operaciones for k, v in inst.items()} == {"bat_G1": 93, "bat_G2": 189, "bat_G3": 280, "bat_G4": 376, "bat_G5": 467}
    assert [inst[g].n_ordenes for g in sorted(inst)] == [10, 20, 30, 40, 50]
    assert [inst["bat_G5"].familias.count(f) for f in range(4)] == [8, 15, 17, 10]      # tabla A.5
    assert inst["bat_G1"].maquinas == (2, 2, 2, 3, 1, 2, 1)
    # el primer lote de G1 (PATH1, F1): 5.0, 4.2, 2.8, 7.6, 2.2, 1.8 y 1.2 h de proceso; 24.8 h en total (tabla A.4)
    assert sum(p for _, p, _ in inst["bat_G1"].trabajos[0]) == 248


def test_variantes_conservan_la_composicion_y_son_reproducibles(inst):
    assert len(EVALUACION) == 25 and len(AJUSTE) == 10 and not set(EVALUACION) & set(AJUSTE)
    for nombre in EVALUACION + AJUSTE:
        v, modo = instancia_bat(nombre)
        g = "bat_" + nombre[4:6]
        assert modo == 0 and v.familias == inst[g].familias and v.maquinas == inst[g].maquinas and v.cambio == inst[g].cambio
        assert instancia_bat(nombre)[0] == v                                                  # misma instancia cada vez
    assert instancia_bat("bat_G2v1")[0].trabajos != instancia_bat("bat_G2v2")[0].trabajos       # y distintas entre sí
    assert instancia_bat("bat_G3#2")[1] == 2 and instancia_bat("bat_G3#2")[0] == inst["bat_G3"]


@pytest.mark.parametrize("nombre", ["bat_G1", "bat_G3v2", "bat_G5t1"])
@pytest.mark.parametrize("modo", [0, 1, 2, 3])
def test_decodificador_de_cpp_igual_al_independiente(nombre, modo):
    i, _ = instancia_bat(nombre)
    pr = ProblemaHFS(i, modo)
    rng = np.random.default_rng(5)
    for _ in range(5):
        prio = rng.random(pr.N)
        mk, ini, maq = pr.decodificar(prio, True)
        mk2, ini2, maq2 = decodificar_py(i, prio, modo)
        assert mk == mk2 and (ini == ini2).all() and (maq == maq2).all()
        assert comprobar(i, ini, maq, modo) == mk
        assert mk >= cota_capacidad(i, modo)


def test_los_modos_cambian_el_makespan(inst):
    pr = [ProblemaHFS(inst["bat_G2"], m) for m in range(4)]
    prio = np.random.default_rng(2).random(pr[0].N)
    mk = [p.decodificar(prio) for p in pr]
    assert mk[1] >= mk[0] and len(set(mk)) > 1                                                   # sumar la fija nunca acorta


def test_el_comprobador_rechaza_lo_invalido(inst):
    pr = ProblemaHFS(inst["bat_G1"])
    mk, ini, maq = pr.decodificar(np.random.default_rng(1).random(pr.N), True)
    malo = ini.copy()
    malo[1] = 0                                                  # la segunda operación del primer lote empieza antes de terminar la primera
    with pytest.raises(AssertionError):
        comprobar(inst["bat_G1"], malo, maq)
    raro = maq.copy()
    raro[0] = 99                                                 # máquina que no es de su etapa
    with pytest.raises(AssertionError):
        comprobar(inst["bat_G1"], ini, raro)
    o1, o2 = [o for o in range(pr.N) if pr.stage[o] == 3][:2]    # dos operaciones del recocido en la misma máquina con bloques solapados
    solap = ini.copy(); m2 = maq.copy()
    m2[o2] = m2[o1]
    solap[o2] = solap[o1]
    with pytest.raises(AssertionError):
        comprobar(inst["bat_G1"], solap, m2)


@pytest.mark.parametrize("modo", [0, 3])
def test_cpsat_con_y_sin_pista_devuelve_calendarios_validos(inst, modo):
    pytest.importorskip("ortools")
    from jsp_ag.exacto_hfs import resolver
    pr = ProblemaHFS(inst["bat_G1"], modo)
    mk0, ini0, maq0 = pr.decodificar(np.random.default_rng(3).random(pr.N), True)
    for pista in (None, (ini0, maq0)):
        r = resolver(inst["bat_G1"], tiempo_s=5.0, hilos=4, con_calendario=True, modo=modo, pista=pista)
        assert r["makespan"] is not None and r["cota"] <= r["makespan"]
        assert comprobar(inst["bat_G1"], r["inicios"], r["maquinas"], modo) == r["makespan"]
        if pista is not None:
            assert r["makespan"] <= mk0                                                          # con pista nunca empeora la pista


def test_ninguna_corrida_bajo_las_cotas():
    from jsp_ag.corridas import BASE
    R = BASE / "resultados"
    if not all((R / n).exists() for n in ("B1_base.csv", "B7_exacto.csv")):
        pytest.skip("faltan los resultados de B1 y B7")
    import pandas as pd
    cp = pd.read_csv(R / "B7_exacto.csv")
    mejor_cota = cp.groupby("instancia")[["cota_cpsat", "cota_capacidad"]].max().max(axis=1)
    d = pd.read_csv(R / "B1_base.csv")
    assert len(d) == 25 * 4 * 30 and not d.duplicated(["instancia", "metodo", "semilla"]).any()
    cap = {n: cota_capacidad(instancia_bat(n)[0]) for n in d["instancia"].unique()}
    assert (d["mejor"].to_numpy() >= d["instancia"].map(cap).to_numpy()).all()
    orig = d[d["instancia"].isin(mejor_cota.index)]
    assert (orig["mejor"].to_numpy() >= orig["instancia"].map(mejor_cota).to_numpy()).all()
