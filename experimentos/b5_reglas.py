"""B5: reglas de despacho (SPT, MWKR, MOPNR) como prioridades fijas en el mismo decodificador, en las 25 instancias y en los cuatro supuestos de modelado
(modo 0 a 3). Uso: python3 b5_reglas.py"""
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from jsp_ag.conjunto_bat import EVALUACION
from jsp_ag.corridas import BASE, problema


def reglas(pr) -> dict:
    spt, mwkr, mopnr, o = [], [], [], 0
    for j in range(len(pr.len)):
        t = pr.pt[o:o + pr.len[j]].astype(float)
        resto = np.cumsum(t[::-1])[::-1]
        spt += list(t)
        mwkr += list(-resto)
        mopnr += list(-np.arange(len(t), 0, -1, dtype=float))
        o += pr.len[j]
    return {"SPT": np.array(spt), "MWKR": np.array(mwkr), "MOPNR": np.array(mopnr)}


def main():
    with open(BASE / "resultados" / "B5_reglas.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["instancia", "modo", "regla", "makespan"])
        for modo in range(4):
            for i in EVALUACION:
                pr = problema(i if modo == 0 else f"{i}#{modo}")
                for nombre, prio in reglas(pr).items():
                    w.writerow([i, modo, nombre, int(pr.decodificar(prio))])


if __name__ == "__main__":
    main()
