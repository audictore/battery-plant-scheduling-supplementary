"""B7: CP-SAT en las cinco instancias originales, 300 s y 8 hilos, sin pista y con pista. La pista es el calendario de una sola corrida del algoritmo genético
(permutación con la configuración de B2, semilla 1000, 29 500 evaluaciones). Cada calendario pasa por el comprobador. Debe correr con la máquina sin otra
carga. Uso: python3 b7_exacto.py [--tiempo 300] [--hilos 8]"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jsp_ag.conjunto_bat import ORIGINALES
from jsp_ag.corridas import BASE, comunes, problema
from jsp_ag.exacto_hfs import resolver
from jsp_ag.hfs import comprobar, cota_capacidad
from jsp_ag.nucleo import Config

p = argparse.ArgumentParser()
p.add_argument("--tiempo", type=float, default=300.0)
p.add_argument("--hilos", type=int, default=8)
a = p.parse_args()
R = BASE / "resultados"
cfg_ag = json.loads((R / "B2_mejor_config.json").read_text(encoding="utf-8"))["permutacion"]
calendarios = {}
with open(R / "B7_exacto.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["instancia", "variante", "estado", "makespan", "cota_cpsat", "cota_capacidad", "segundos", "limite_s", "hilos", "semilla", "makespan_pista", "segundos_pista"])
    for nombre in ORIGINALES:
        pr = problema(nombre)
        inst = pr.inst
        t0 = time.perf_counter()
        r = pr.ejecutar("permutacion", 1000, Config.con_presupuesto(29500, pop=cfg_ag["pop"], escala_mutacion=cfg_ag["escala"], **comunes("permutacion")))
        mk0, ini0, maq0 = pr.decodificar(r["prio"], True)
        seg0 = time.perf_counter() - t0
        assert mk0 == r["mejor"]
        comprobar(inst, ini0, maq0)
        for variante in ("sin_pista", "con_pista"):
            res = resolver(inst, tiempo_s=a.tiempo, hilos=a.hilos, semilla=1, con_calendario=True, pista=(ini0, maq0) if variante == "con_pista" else None)
            if res["makespan"] is not None:
                assert comprobar(inst, res["inicios"], res["maquinas"]) == res["makespan"], f"{nombre}: calendario de CP-SAT inválido"
                calendarios[f"{nombre}|{variante}"] = {"inicios": [int(x) for x in res["inicios"]], "maquinas": [int(x) for x in res["maquinas"]], "makespan": res["makespan"]}
            w.writerow([nombre, variante, res["estado"], res["makespan"], res["cota"], cota_capacidad(inst), round(res["segundos"], 2), a.tiempo, a.hilos, 1, mk0, round(seg0, 2)])
            f.flush()
            print(f"{nombre} {variante}: {res['estado']} makespan {res['makespan']} cota {res['cota']} (pista {mk0})", flush=True)
calendarios["AG"] = {}
(R / "B7_calendarios.json").write_text(json.dumps(calendarios), encoding="utf-8")
