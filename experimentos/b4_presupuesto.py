"""B4: una corrida larga (300 000 evaluaciones) por semilla en las cinco instancias originales; el mejor makespan se lee luego a 10 000, 30 000,
100 000 y 300 000 evaluaciones. 20 semillas (1000 a 1019). Uso: python3 b4_presupuesto.py [--procesos 7]"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jsp_ag.conjunto_bat import METODOS, ORIGINALES
from jsp_ag.corridas import BASE, correr, semillas


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--procesos", type=int, default=7)
    a = p.parse_args()
    tareas = [dict(experimento="B4", instancia=i, metodo=m, presupuesto=300000, semilla=s, curva=True) for i in ORIGINALES for m in METODOS + ("aleatoria",) for s in semillas(20)]
    correr(tareas, BASE / "resultados" / "B4_presupuesto.csv", BASE / "resultados" / "B4_curvas.npz", procesos=a.procesos)


if __name__ == "__main__":
    main()
