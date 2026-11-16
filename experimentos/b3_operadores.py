"""B3: cada codificación con cada cruza que admite (la binaria también con código Gray): 12 variantes, parámetros base, 25 instancias, 30 semillas.
Uso: python3 b3_operadores.py [--procesos 7]"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jsp_ag.conjunto_bat import EVALUACION
from jsp_ag.corridas import BASE, correr, semillas
from jsp_ag.nucleo import CRUZA


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--procesos", type=int, default=7)
    a = p.parse_args()
    variantes = []
    for cod, ops in CRUZA.items():
        for op in ops:
            variantes.append((cod, op, False))
            if cod == "binaria":
                variantes.append((cod, op, True))
    tareas = [dict(experimento="B3", instancia=i, metodo=m, cruza=op, gray=g, presupuesto=29500, semilla=s)
              for i in EVALUACION for (m, op, g) in variantes for s in semillas(30)]
    correr(tareas, BASE / "resultados" / "B3_operadores.csv", procesos=a.procesos)


if __name__ == "__main__":
    main()
