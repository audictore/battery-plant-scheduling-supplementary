"""Análisis del estudio de la planta de baterías. Los makespan están en décimas de hora; las brechas, en %.

Referencia de cada instancia (mejor valor conocido, MVC) = el menor makespan hallado por cualquier método en cualquier experimento con el supuesto
base (modo 0), incluidos los calendarios de CP-SAT. Cota inferior = el mayor entre la cota por capacidad del recocido y la cota de CP-SAT (solo
en las cinco originales). Las brechas son contra el MVC; las «brechas a la cota» acotan por arriba lo lejos que se puede estar del óptimo."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from . import estadistica as est

RES = Path(__file__).resolve().parents[1] / "resultados"
METODOS = ["binaria", "permutacion", "llaves"]
TODOS = METODOS + ["aleatoria"]
NOMBRE = {"binaria": "Binaria", "permutacion": "Permutación", "llaves": "Llaves", "aleatoria": "Aleatoria"}
GRUPOS = ["G1", "G2", "G3", "G4", "G5"]
ARCHIVOS_MODO_BASE = ("B1_base.csv", "B2b_ajustado.csv", "B2d_ajustado.csv", "B3_operadores.csv", "B4_presupuesto.csv", "B8_bits.csv")


def _csv(n):
    return pd.read_csv(RES / n)


def instancia_base(nombre: str) -> str:
    return nombre.split("#")[0]


def referencias() -> pd.DataFrame:
    """Una fila por instancia (las 25 de evaluación): MVC, cota por capacidad, cota de CP-SAT y mejor cota."""
    from jsp_ag.conjunto_bat import EVALUACION
    from jsp_ag.hfs import cota_capacidad, instancia_bat
    partes = [_csv(n)[["instancia", "mejor"]] for n in ARCHIVOS_MODO_BASE if (RES / n).exists()]
    d = pd.concat(partes)
    d = d[~d["instancia"].str.contains("#")]
    mvc = d.groupby("instancia")["mejor"].min().reindex(EVALUACION)
    r = pd.DataFrame({"mvc_ag": mvc})
    r["cota_cap"] = pd.Series({n: cota_capacidad(instancia_bat(n)[0]) for n in EVALUACION})
    r["cota_cpsat"] = np.nan
    r["cpsat_sin"] = np.nan
    r["cpsat_con"] = np.nan
    if (RES / "B7_exacto.csv").exists():
        cp = _csv("B7_exacto.csv")
        for v, col in (("sin_pista", "cpsat_sin"), ("con_pista", "cpsat_con")):
            x = cp[cp["variante"] == v].set_index("instancia")
            r.loc[x.index, col] = x["makespan"]
        r.loc[cp["instancia"].unique(), "cota_cpsat"] = cp.groupby("instancia")["cota_cpsat"].max()
    r["mvc"] = r[["mvc_ag", "cpsat_sin", "cpsat_con"]].min(axis=1)
    r["cota"] = r[["cota_cap", "cota_cpsat"]].max(axis=1)
    return r


def con_brecha(d: pd.DataFrame, ref: pd.Series, col: str = "gap") -> pd.DataFrame:
    d = d.copy()
    r = d["instancia"].map(ref)
    d[col] = 100 * (d["mejor"] - r) / r
    return d


def tamano(inst: str) -> str:
    return instancia_base(inst)[4:6]


def medianas(d: pd.DataFrame, por: list, col="gap") -> pd.DataFrame:
    """Mediana de las 30 corridas por instancia y por las columnas de `por` (método, variante...). Filas = instancias."""
    return d.groupby(["instancia"] + por)[col].median().unstack(por)


def friedman_rangos(m: pd.DataFrame):
    chi, p, rangos = est.friedman(m.to_numpy())
    return chi, p, dict(zip(m.columns, rangos))


def holm_pares(m: pd.DataFrame, pares: list):
    """Wilcoxon por pares sobre las medianas por instancia, con Holm. Devuelve filas (a, b, media a, media b, #a<b, #empates, #a>b, p, p Holm)."""
    ps = []
    for a, b in pares:
        x, y = m[a].to_numpy(), m[b].to_numpy()
        ps.append(1.0 if np.all(x == y) else float(stats.wilcoxon(x, y, zero_method="wilcox").pvalue))
    ph = est.holm(ps)
    out = []
    for (a, b), p, q in zip(pares, ps, ph):
        x, y = m[a], m[b]
        out.append((a, b, float(x.mean()), float(y.mean()), int((x < y).sum()), int((x == y).sum()), int((x > y).sum()), p, float(q)))
    return out
