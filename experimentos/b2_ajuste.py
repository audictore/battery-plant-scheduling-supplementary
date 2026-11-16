"""B2: parámetros. (a) Rejilla de escala de la mutación (0 a 8 veces la tasa base) por tamaño de la población (50 a 800), en las 10 instancias de ajuste
(semillas 5000 en adelante, 5 por celda), para cada codificación, con los parámetros comunes de B0. (b) La mejor celda de cada una, en las 25 de evaluación con las semillas 1000 a 1029.
Uso: python3 b2_ajuste.py [--procesos 7]"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from jsp_ag.conjunto_bat import AJUSTE, EVALUACION, METODOS
from jsp_ag.corridas import BASE, correr, semillas

ESCALAS, POBLACIONES = (0.0, 0.03125, 0.0625, 0.125, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0), (50, 100, 200, 400, 800)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--procesos", type=int, default=7)
    a = p.parse_args()
    R = BASE / "resultados"
    tareas = [dict(experimento="B2a", instancia=i, metodo=m, escala=e, pop=pop, presupuesto=29500, semilla=5000 + s)
              for i in AJUSTE for m in METODOS for e in ESCALAS for pop in POBLACIONES for s in range(5)]
    d = pd.DataFrame(correr(tareas, R / "B2a_rejilla.csv", procesos=a.procesos))
    d["conf"] = list(zip(d["escala"], d["pop"]))
    m = d.groupby(["metodo", "instancia", "conf"])["mejor"].mean().reset_index()
    m["rel"] = m["mejor"] / m.groupby(["metodo", "instancia"])["mejor"].transform("min")
    puntaje = m.groupby(["metodo", "conf"])["rel"].mean().reset_index()
    mejores = {}
    for cod in METODOS:
        s = puntaje[puntaje["metodo"] == cod].sort_values("rel")
        escala, pop = s.iloc[0]["conf"]
        mejores[cod] = {"escala": float(escala), "pop": int(pop), "rel_ajuste": float(s.iloc[0]["rel"])}
        print(f"mejor configuración de {cod}: escala {escala}, población {pop} (relativo {s.iloc[0]['rel']:.4f})")
    (R / "B2_mejor_config.json").write_text(json.dumps(mejores, indent=1), encoding="utf-8")
    tareas = [dict(experimento="B2b", instancia=i, metodo=cod, escala=c["escala"], pop=c["pop"], presupuesto=29500, semilla=s)
              for i in EVALUACION for cod, c in mejores.items() for s in semillas(30)]
    correr(tareas, R / "B2b_ajustado.csv", procesos=a.procesos)


if __name__ == "__main__":
    main()
