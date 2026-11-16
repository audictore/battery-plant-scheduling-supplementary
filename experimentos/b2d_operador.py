"""B2d: ajuste propio de cada cruza. B2 ajustó cada codificación con su cruza base (binaria con dos puntos, llaves con uniforme). Aquí se ajustan con la misma rejilla
(10 escalas × 5 poblaciones, 5 semillas por celda, 10 instancias de ajuste) las otras dos combinaciones (binaria con uniforme, llaves con dos puntos) y se evalúan
en las 25 instancias con 30 semillas. Así la comparación entre binaria y llaves no depende de que una cruza haya recibido ajuste y la otra no.
Uso: python3 b2d_operador.py [--procesos 7]"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from jsp_ag.conjunto_bat import AJUSTE, EVALUACION
from jsp_ag.corridas import BASE, correr, semillas

ESCALAS, POBLACIONES = (0.0, 0.03125, 0.0625, 0.125, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0), (50, 100, 200, 400, 800)
COMBOS = (("binaria", "uniforme"), ("llaves", "dos_puntos"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--procesos", type=int, default=7)
    a = p.parse_args()
    R = BASE / "resultados"
    tareas = [dict(experimento="B2d", instancia=i, metodo=m, cruza=c, escala=e, pop=pop, presupuesto=29500, semilla=5000 + s)
              for i in AJUSTE for m, c in COMBOS for e in ESCALAS for pop in POBLACIONES for s in range(5)]
    d = pd.DataFrame(correr(tareas, R / "B2d_rejilla.csv", procesos=a.procesos))
    d["conf"] = list(zip(d["escala"], d["pop"]))
    m = d.groupby(["metodo", "cruza", "instancia", "conf"])["mejor"].mean().reset_index()
    m["rel"] = m["mejor"] / m.groupby(["metodo", "cruza", "instancia"])["mejor"].transform("min")
    puntaje = m.groupby(["metodo", "cruza", "conf"])["rel"].mean().reset_index()
    mejores = {}
    for met, cr in COMBOS:
        s = puntaje[(puntaje["metodo"] == met) & (puntaje["cruza"] == cr)].sort_values("rel")
        escala, pop = s.iloc[0]["conf"]
        mejores[f"{met}/{cr}"] = {"metodo": met, "cruza": cr, "escala": float(escala), "pop": int(pop), "rel_ajuste": float(s.iloc[0]["rel"])}
        print(f"mejor configuración de {met} con {cr}: escala {escala}, población {pop} (relativo {s.iloc[0]['rel']:.4f})")
    (R / "B2d_mejor_config.json").write_text(json.dumps(mejores, indent=1), encoding="utf-8")
    tareas = [dict(experimento="B2d", instancia=i, metodo=c["metodo"], cruza=c["cruza"], escala=c["escala"], pop=c["pop"], presupuesto=29500, semilla=s)
              for i in EVALUACION for c in mejores.values() for s in semillas(30)]
    correr(tareas, R / "B2d_ajustado.csv", procesos=a.procesos)


if __name__ == "__main__":
    main()
