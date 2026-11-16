"""Auditoría (16-nov-2026): repite al azar (semilla 7) 10 corridas de cada archivo de resultados con el mismo código y la misma semilla, y comprueba que dan
el mismo makespan que el CSV. Es una prueba de reproducibilidad (determinismo, parámetros bien registrados), no de independencia: usa el código del estudio."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "experimentos"))
from jsp_ag.corridas import _una  # noqa: E402

R = RAIZ / "experimentos" / "resultados"
rng = np.random.default_rng(7)
mal = 0
for a in ("B0a_comunes.csv", "B0b_confirmacion.csv", "B1_base.csv", "B2b_ajustado.csv", "B2d_ajustado.csv", "B3_operadores.csv", "B6_supuestos.csv", "B8_bits.csv", "B2a_rejilla.csv"):
    d = pd.read_csv(R / a)
    d = d[d["instancia"].str.contains("G1|G2")]                         # instancias chicas: la repetición es rápida
    ok = 0
    for _, f in d.iloc[rng.choice(len(d), 10, replace=False)].iterrows():
        t = {k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in f.to_dict().items()}
        tarea = dict(instancia=t["instancia"], metodo=t["metodo"], presupuesto=int(t["presupuesto"]), semilla=int(t["semilla"]), pop=int(t["pop"]) if t["pop"] else 100,
                     escala=float(t["escala"]) if t["escala"] is not None else 1.0, cruza=t["cruza"] if isinstance(t["cruza"], str) else None,
                     gray=str(t["gray"]).lower() == "true", bits=int(t["bits"]) if t["bits"] is not None else 8,
                     elite=int(t["elite"]), torneo=int(t["torneo"]), pc=float(t["pc"]), sigma=float(t["sigma"]))
        fila, _, _ = _una(tarea)
        ok += fila["mejor"] == int(t["mejor"])
    print(f"{'OK  ' if ok == 10 else 'MAL '}{a}: {ok} de 10 corridas repetidas dan el mismo makespan")
    mal += ok != 10
print("\nReproducción:", "sin discrepancias" if not mal else f"{mal} archivos con discrepancias")
