"""B0: ajuste de los parámetros comunes del algoritmo genético (tamaño del torneo, elitismo, probabilidad de cruza y, solo en las llaves, la desviación
de la mutación) con las 10 instancias de ajuste de la planta, con población 100 y escala de mutación 1 (la celda de referencia de B2).
Etapa 1: todas las combinaciones de la rejilla, 3 semillas por instancia (5000 a 5002). Etapa 2: las mejores 5 de cada codificación más la configuración
de partida, con 10 semillas nuevas (5013 a 5022), para no elegir con las mismas corridas que las seleccionaron. Se elige la mejor de la etapa 2.
La rejilla se corrió en dos tandas: la primera sin elitismo 0 y con sigma hasta 0.30; como las mejores celdas cayeron en esos bordes, la segunda las
completa (elitismo 0 y sigma 0.5 y 0.75). Este guion corre solo las combinaciones que faltan en B0a_comunes.csv.
Salidas: resultados/B0a_comunes.csv, B0b_confirmacion.csv y B0_mejor_config.json. Uso: python3 b0_comunes.py [--procesos 7]"""
import argparse
import itertools
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from jsp_ag.conjunto_bat import AJUSTE, METODOS
from jsp_ag.corridas import BASE, correr

TORNEOS, ELITES, CRUZAS, SIGMAS = (2, 3, 5, 7), (0, 1, 2, 5, 10), (0.6, 0.8, 0.9, 1.0), (0.05, 0.15, 0.30, 0.5, 0.75)
PARTIDA = dict(torneo=3, elite=2, pc=0.9, sigma=0.15)
CLAVES = ("torneo", "elite", "pc", "sigma")


def rejilla(cod):
    for t, e, c in itertools.product(TORNEOS, ELITES, CRUZAS):
        for s in (SIGMAS if cod == "llaves" else (PARTIDA["sigma"],)):
            yield dict(torneo=t, elite=e, pc=c, sigma=s)


def puntaje(d):
    """Makespan medio de cada configuración en cada instancia, relativo al mejor de esa instancia; promedio de las instancias."""
    m = d.groupby(["metodo", *CLAVES, "instancia"])["mejor"].mean().reset_index()
    m["rel"] = m["mejor"] / m.groupby(["metodo", "instancia"])["mejor"].transform("min")
    return m.groupby(["metodo", *CLAVES])["rel"].mean().reset_index()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--procesos", type=int, default=7)
    a = p.parse_args()
    R = BASE / "resultados"
    ruta = R / "B0a_comunes.csv"
    previo = pd.read_csv(ruta) if ruta.exists() else pd.DataFrame(columns=["metodo", "instancia", "semilla", *CLAVES])
    hechas = set(zip(previo["metodo"], previo["instancia"], previo["semilla"], previo["torneo"], previo["elite"], previo["pc"].round(6), previo["sigma"].round(6)))
    tareas = [dict(experimento="B0a", instancia=i, metodo=m, presupuesto=29500, semilla=5000 + s, **c)
              for m in METODOS for c in rejilla(m) for i in AJUSTE for s in range(3)
              if (m, i, 5000 + s, c["torneo"], c["elite"], round(c["pc"], 6), round(c["sigma"], 6)) not in hechas]
    print(f"{len(tareas)} corridas nuevas en la etapa 1", flush=True)
    if tareas:
        nuevas = pd.DataFrame(correr(tareas, R / "B0a_nuevas.csv", procesos=a.procesos))
        previo = pd.concat([previo, nuevas])
        previo.to_csv(ruta, index=False)
    s1 = puntaje(previo)
    finalistas = []
    for m in METODOS:
        top = s1[s1["metodo"] == m].sort_values("rel").head(5)
        cand = [{k: r[k] for k in CLAVES} for _, r in top.iterrows()]
        if not any(all(abs(c[k] - PARTIDA[k]) < 1e-9 for k in CLAVES) for c in cand):
            cand.append(dict(PARTIDA))
        finalistas += [(m, c) for c in cand]
    tareas = [dict(experimento="B0b", instancia=i, metodo=m, presupuesto=29500, semilla=5013 + s, **c)
              for m, c in finalistas for i in AJUSTE for s in range(10)]
    d2 = pd.DataFrame(correr(tareas, R / "B0b_confirmacion.csv", procesos=a.procesos))
    s2 = puntaje(d2)
    mejores = {}
    for m in METODOS:
        t = s2[s2["metodo"] == m].sort_values("rel")
        b = t.iloc[0]
        ref = t[(t["torneo"] == PARTIDA["torneo"]) & (t["elite"] == PARTIDA["elite"]) & (abs(t["pc"] - PARTIDA["pc"]) < 1e-9) & (abs(t["sigma"] - PARTIDA["sigma"]) < 1e-9)].iloc[0]
        mejores[m] = {**{k: float(b[k]) if k in ("pc", "sigma") else int(b[k]) for k in CLAVES}, "rel_confirmacion": float(b["rel"]), "rel_partida": float(ref["rel"])}
        print(f"{m}: mejor {mejores[m]}")
    (R / "B0_mejor_config.json").write_text(json.dumps(mejores, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
