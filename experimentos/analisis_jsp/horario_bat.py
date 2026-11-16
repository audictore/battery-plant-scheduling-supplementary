"""Horario de trabajo propuesto para el grupo G1 (10 lotes, el único cuya lista viene completa en el conjunto de datos): el mejor calendario conocido, el de la
regla MOPNR para comparar, la figura (Gantt), la tabla de secuencias del recocido y el libro de Excel para la planta (resultados/horario_G1.xlsx).
`calcular()` repite las corridas del algoritmo genético con su semilla y comprueba que dan el makespan del CSV; todo calendario pasa por `comprobar`."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .bat import RES

BASE = Path(__file__).resolve().parents[1]
FAM = ["F1", "F2", "F3", "F4"]


def mejor_corrida_ag(nombre: str) -> dict:
    """La corrida de AG con menor makespan en el modo base de B1, B2b, B2d, B3 y B8 (la primera si hay empate)."""
    partes = []
    for a in ("B1_base.csv", "B2b_ajustado.csv", "B2d_ajustado.csv", "B3_operadores.csv", "B8_bits.csv"):
        if (RES / a).exists():
            d = pd.read_csv(RES / a)
            partes.append(d[(d["instancia"] == nombre) & (d["metodo"] != "aleatoria")].assign(archivo=a))
    d = pd.concat(partes)
    d = d.sort_values(["mejor", "archivo", "semilla"]).iloc[0]
    return d.to_dict()


def calendario_ag(nombre: str):
    from jsp_ag.corridas import problema
    from jsp_ag.nucleo import Config
    t = mejor_corrida_ag(nombre)
    pr = problema(nombre)
    cruza = t["cruza"] if isinstance(t["cruza"], str) else None
    cfg = Config.con_presupuesto(int(t["presupuesto"]), pop=int(t["pop"]) if not np.isnan(t["pop"]) else 100, escala_mutacion=float(t["escala"]) if not np.isnan(t["escala"]) else 1.0,
                                 gray=str(t["gray"]).lower() == "true", cruza=cruza, bits=int(t["bits"]) if not np.isnan(t["bits"]) else 8,
                                 elite=int(t["elite"]), torneo=int(t["torneo"]), pc=float(t["pc"]), sigma=float(t["sigma"]))
    r = pr.ejecutar(t["metodo"], int(t["semilla"]), cfg)
    assert r["mejor"] == int(t["mejor"]), f"la corrida repetida da {r['mejor']} y el CSV {t['mejor']}"
    mk, ini, maq = pr.decodificar(r["prio"], True)
    assert mk == int(t["mejor"])
    return mk, ini, maq, t


def calendario_regla(nombre: str, regla: str = "MOPNR"):
    from b5_reglas import reglas
    from jsp_ag.corridas import problema
    pr = problema(nombre)
    mk, ini, maq = pr.decodificar(reglas(pr)[regla], True)
    return mk, ini, maq


def calendarios_g1() -> dict:
    from jsp_ag.corridas import problema
    from jsp_ag.hfs import comprobar
    nombre = "bat_G1"
    inst = problema(nombre).inst
    out = {}
    mk, ini, maq = calendario_regla(nombre)
    out["MOPNR"] = {"makespan": int(mk), "inicios": ini.tolist(), "maquinas": maq.tolist()}
    mk, ini, maq, t = calendario_ag(nombre)
    out["AG"] = {"makespan": int(mk), "inicios": ini.tolist(), "maquinas": maq.tolist(), "metodo": t["metodo"], "cruza": t["cruza"] if isinstance(t["cruza"], str) else "", "semilla": int(t["semilla"]),
                 "archivo": t["archivo"]}
    cp = json.loads((RES / "B7_calendarios.json").read_text(encoding="utf-8"))
    for v in ("sin_pista", "con_pista"):
        k = f"{nombre}|{v}"
        if k in cp:
            out["CPSAT_" + v] = cp[k]
    for k, c in out.items():
        assert comprobar(inst, c["inicios"], c["maquinas"]) == c["makespan"], k
    out["mejor"] = min((k for k in out), key=lambda k: out[k]["makespan"] if k != "MOPNR" else 10 ** 9)
    (RES / "horario_G1.json").write_text(json.dumps(out), encoding="utf-8")
    return out


def cargar() -> dict:
    return json.loads((RES / "horario_G1.json").read_text(encoding="utf-8"))


def secuencia_recocido(inst, c: dict) -> list:
    """Por máquina de recocido: lista de (lote, familia, inicio de la preparación, inicio del proceso, fin, preparación) ordenada en el tiempo."""
    from .figuras_bat import bloques
    b = bloques(inst, c["inicios"], c["maquinas"])
    e = inst.etapa_seq
    moff = int(sum(inst.maquinas[:e]))
    por = {m: [] for m in range(moff, moff + inst.maquinas[e])}
    for m, s0, s1, e1, j, k, s in b:
        if m in por:
            por[m].append((j, inst.familias[j], s0, s1, e1, s))
    return [sorted(v, key=lambda x: x[3]) for _, v in sorted(por.items())]


def resumen(inst, c: dict) -> dict:
    sec = secuencia_recocido(inst, c)
    cambios = sum(1 for m in sec for a, b in zip(m, m[1:]) if a[1] != b[1])
    prep = sum(x[5] for m in sec for x in m)
    ocup = [sum(x[4] - x[2] for x in m) / c["makespan"] for m in sec]
    return {"cambios": cambios, "prep_recocido_h": prep / 10, "ocupacion_pct": [100 * o for o in ocup], "makespan_h": c["makespan"] / 10}


def tardanzas(inst, c: dict) -> list:
    """Por lote de G1: (id, familia, fecha de entrega, fin del lote, retraso), en horas. Las fechas de entrega son las de la tabla A.4 del conjunto de datos; el
    objetivo del estudio no las usa."""
    d = json.loads((BASE / "instancias" / "baterias_parametros.json").read_text(encoding="utf-8"))
    offs = np.concatenate([[0], np.cumsum([len(x) for x in inst.trabajos])])
    out = []
    for j, lote in enumerate(d["G1_trabajos"]):
        u = int(offs[j + 1]) - 1
        fin = (int(c["inicios"][u]) + inst.trabajos[j][-1][1]) / 10
        out.append((lote["id"], lote["familia"], lote["entrega"], fin, max(0.0, fin - lote["entrega"])))
    return out


def tabla_secuencias(inst, c: dict) -> str:
    from .tablas_bat import tabular
    filas = []
    for i, m in enumerate(secuencia_recocido(inst, c)):
        seq = " ".join(f"B{j + 1}" for j, *_ in m)
        fam = " ".join(FAM[f][1] for _, f, *_ in m)
        filas.append(f"Recocido {i + 1} & {seq} & {fam} \\\\")
    return tabular(r"@{}l >{\RaggedRight\arraybackslash}p{0.36\columnwidth} >{\RaggedRight\arraybackslash}p{0.27\columnwidth}@{}", "Máquina & Lotes en orden & Familias", filas)


def libro_excel(inst, c: dict, ruta, ref: dict) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from .figuras_bat import NOMBRES_ETAPA, bloques
    d = json.loads((BASE / "instancias" / "baterias_parametros.json").read_text(encoding="utf-8"))
    lotes = d["G1_trabajos"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Operaciones"
    cab = ["Lote", "Familia", "Ruta", "Operación", "Etapa", "Máquina", "Inicio de la preparación (h)", "Inicio del proceso (h)", "Fin (h)", "Preparación (h)", "Proceso (h)"]
    ws.append(cab)
    offs = np.concatenate([[0], np.cumsum([len(t) for t in inst.trabajos])])
    moff = np.concatenate([[0], np.cumsum(inst.maquinas)])
    filas = sorted(bloques(inst, c["inicios"], c["maquinas"]), key=lambda b: (b[4], b[5]))
    for m, s0, s1, e1, j, k, s in filas:
        et = inst.trabajos[j][k][0]
        ws.append([lotes[j]["id"], lotes[j]["familia"], lotes[j]["ruta"], k + 1, NOMBRES_ETAPA[et], f"{NOMBRES_ETAPA[et]} {m - int(moff[et]) + 1}" if inst.maquinas[et] > 1 else NOMBRES_ETAPA[et],
                   s0 / 10, s1 / 10, e1 / 10, s / 10, (e1 - s1) / 10])
    ws2 = wb.create_sheet("Secuencia por máquina")
    ws2.append(["Máquina", "Orden", "Lote", "Familia", "Inicio de la preparación (h)", "Inicio del proceso (h)", "Fin (h)", "Preparación (h)"])
    nombres = []
    for et, q in enumerate(inst.maquinas):
        nombres += [f"{NOMBRES_ETAPA[et]} {i + 1}" if q > 1 else NOMBRES_ETAPA[et] for i in range(q)]
    for m in range(int(moff[-1])):
        lista = sorted([b for b in filas if b[0] == m], key=lambda b: b[2])
        for n, (mm, s0, s1, e1, j, k, s) in enumerate(lista, 1):
            ws2.append([nombres[m], n, lotes[j]["id"], lotes[j]["familia"], s0 / 10, s1 / 10, e1 / 10, s / 10])
    ws4 = wb.create_sheet("Lotes y fechas de entrega")
    ws4.append(["Lote", "Familia", "Fecha de entrega (h)", "Fin del lote (h)", "Retraso (h)"])
    for lote_id, fam_id, entrega, fin, ret in tardanzas(inst, c):
        ws4.append([lote_id, fam_id, entrega, fin, ret])
    ws4.append([])
    ws4.append(["Nota", "Las fechas de entrega son las del conjunto de datos; este calendario minimiza el tiempo total y no las usa."])
    ws3 = wb.create_sheet("Resumen")
    r = resumen(inst, c)
    for fila in (["Instancia", "G1 del conjunto de datos (10 lotes, 93 operaciones)"], ["Tiempo total (h)", r["makespan_h"]], ["Cota inferior (h)", ref["cota"] / 10],
                 ["Regla de despacho MOPNR (h)", ref["mopnr"] / 10], ["Horas ganadas frente a MOPNR", (ref["mopnr"] - c["makespan"]) / 10],
                 ["Cambios de familia en el recocido", r["cambios"]], ["Preparación total en el recocido (h)", r["prep_recocido_h"]],
                 ["Ocupación del recocido 1/2/3 (%)", " / ".join(f"{x:.0f}" for x in r["ocupacion_pct"])],
                 [], ["Supuestos", "Operación continua (24 h); el tiempo 0 es el inicio del primer lote; sin averías, traslados ni límites de espacio entre etapas; "
                      "el cambio entre familias sustituye a la preparación fija del recocido. Las fechas de entrega del conjunto de datos no se usaron."],
                 ["Origen", "Calendario calculado por programa (algoritmo genético / CP-SAT) y revisado con un comprobador independiente de precedencias, máquinas y solapes."]):
        ws3.append(fila)
    for w in (ws, ws2, ws4, ws3):
        for cel in w[1]:
            cel.font = Font(bold=True)
            cel.fill = PatternFill("solid", fgColor="DDDDDD")
            cel.alignment = Alignment(wrap_text=True, vertical="center")
        for i, col in enumerate(w.columns, 1):
            w.column_dimensions[get_column_letter(i)].width = 22 if w is not ws3 else (36 if i == 1 else 90)
        w.freeze_panes = "A2"
    wb.save(ruta)
