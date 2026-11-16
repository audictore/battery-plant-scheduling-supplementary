"""B6: sensibilidad a los supuestos de modelado. En las cinco instancias originales, los cuatro métodos con parámetros base en los modos 1 a 3 del
decodificador (el 0 es B1): 1 = el cambio de familia se suma a la preparación fija; 2 = la preparación puede adelantarse a la llegada del lote;
3 = ambos. 30 semillas. Uso: python3 b6_supuestos.py [--procesos 7]"""
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
    tareas = [dict(experimento="B6", instancia=f"{i}#{modo}", metodo=m, presupuesto=29500, semilla=s)
              for i in ORIGINALES for modo in (1, 2, 3) for m in METODOS + ("aleatoria",) for s in semillas(30)]
    correr(tareas, BASE / "resultados" / "B6_supuestos.csv", procesos=a.procesos)


if __name__ == "__main__":
    main()
