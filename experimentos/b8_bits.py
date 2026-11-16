"""B8: resolución de la binaria. Con 8 bits por operación hay 256 prioridades distintas y hasta 467 operaciones, así que hay empates que el decodificador rompe siempre
a favor del menor índice. Se repite la binaria con 4, 12 y 16 bits (cruza de dos puntos y uniforme, parámetros base) en las 25 instancias, 30 semillas; con 8 bits
son los resultados de B3. Uso: python3 b8_bits.py [--procesos 7]"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jsp_ag.conjunto_bat import EVALUACION
from jsp_ag.corridas import BASE, correr, semillas


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--procesos", type=int, default=7)
    a = p.parse_args()
    tareas = [dict(experimento="B8", instancia=i, metodo="binaria", cruza=c, bits=b, presupuesto=29500, semilla=s)
              for i in EVALUACION for c in ("dos_puntos", "uniforme") for b in (4, 12, 16) for s in semillas(30)]
    correr(tareas, BASE / "resultados" / "B8_bits.csv", procesos=a.procesos)


if __name__ == "__main__":
    main()
