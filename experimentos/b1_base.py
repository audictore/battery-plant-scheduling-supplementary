"""B1: las tres codificaciones y la búsqueda aleatoria con los parámetros base, 29 500 evaluaciones, en las 25 instancias de evaluación, 30 semillas
(1000 a 1029). Uso: python3 b1_base.py [--procesos 7]"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jsp_ag.conjunto_bat import EVALUACION, METODOS
from jsp_ag.corridas import BASE, correr, semillas


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--procesos", type=int, default=7)
    a = p.parse_args()
    tareas = [dict(experimento="B1", instancia=i, metodo=m, presupuesto=29500, semilla=s) for i in EVALUACION for m in METODOS + ("aleatoria",) for s in semillas(30)]
    correr(tareas, BASE / "resultados" / "B1_base.csv", procesos=a.procesos)


if __name__ == "__main__":
    main()
