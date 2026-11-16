"""Corridas en paralelo: cada una depende solo de su semilla. Escribe un CSV con una fila por corrida y, si se pide, un .npz con las curvas."""
from __future__ import annotations

import csv
import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from .nucleo import Config, Problema

BASE = Path(__file__).resolve().parents[1]
SEMILLA_BASE = 1000                   # las corridas de evaluación usan las semillas 1000, 1001, …
_CACHE: dict = {}
_COMUNES: dict = {}
PARTIDA = dict(torneo=3, elite=2, pc=0.9, sigma=0.15)      # solo para cuando aún no existe B0_mejor_config.json (el propio B0 pasa todos sus valores)


def comunes(metodo: str) -> dict:
    """Torneo, elitismo, probabilidad de cruza y sigma de cada codificación: los que eligió B0 con las instancias de ajuste de la planta."""
    if not _COMUNES:
        ruta = BASE / "resultados" / "B0_mejor_config.json"
        _COMUNES.update(json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {"vacio": True})
    c = _COMUNES.get(metodo, {})
    return {k: type(v)(c.get(k, v)) for k, v in PARTIDA.items()}


def problema(nombre: str) -> Problema:
    if nombre not in _CACHE:
        if not nombre.startswith("bat_"):
            raise KeyError(f"instancia desconocida: {nombre} (solo hay instancias de la planta, «bat_…»)")
        from .hfs import ProblemaHFS, instancia_bat
        inst, modo = instancia_bat(nombre)
        _CACHE[nombre] = ProblemaHFS(inst, modo)
    return _CACHE[nombre]


def _una(t: dict):
    """Una corrida. `t` describe la instancia, el método, la configuración y la semilla."""
    pr = problema(t["instancia"])
    c = comunes(t["metodo"])
    cfg = Config.con_presupuesto(t["presupuesto"], pop=t.get("pop", 100), elite=t.get("elite", c["elite"]), torneo=t.get("torneo", c["torneo"]),
                                 pc=t.get("pc", c["pc"]), escala_mutacion=t.get("escala", 1.0), sigma=t.get("sigma", c["sigma"]),
                                 gray=t.get("gray", False), cruza=t.get("cruza"), bits=t.get("bits", 8))
    t0 = time.perf_counter()
    r = pr.ejecutar(t["metodo"], t["semilla"], cfg, diversidad=t.get("diversidad", False))
    dt = time.perf_counter() - t0
    fila = {**{k: t.get(k, "") for k in ("experimento", "instancia", "metodo", "cruza", "gray", "bits", "pop", "escala", "presupuesto", "semilla")},
            "elite": cfg.elite, "torneo": cfg.torneo, "pc": cfg.pc, "sigma": cfg.sigma,
            "generaciones": cfg.gens, "evaluaciones": r["evaluaciones"], "mejor": r["mejor"], "tiempo_s": round(dt, 4)}
    return fila, (r["curva"] if t.get("curva") else None), (r["diversidad"] if t.get("diversidad") else None)


def correr(tareas: list, salida_csv: Path, salida_npz: Path | None = None, procesos: int = 7, quieto: bool = False):
    """Ejecuta todas las tareas en paralelo, escribe el CSV (una fila por corrida) y, si hay curvas, el .npz."""
    salida_csv = Path(salida_csv)
    salida_csv.parent.mkdir(parents=True, exist_ok=True)
    filas, curvas, divs = [], {}, {}
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=procesos) as ex:
        for i, (fila, curva, div) in enumerate(ex.map(_una, tareas, chunksize=4)):
            filas.append(fila)
            clave = f'{fila["experimento"]}|{fila["instancia"]}|{fila["metodo"]}|{fila["cruza"]}|{int(bool(fila["gray"]))}|{fila["pop"]}|{fila["escala"]}|{fila["presupuesto"]}|{fila["semilla"]}'
            if curva is not None:
                curvas[clave] = curva
            if div is not None:
                divs["div|" + clave] = div.astype(np.float32)
            if not quieto and (i + 1) % 1000 == 0:
                print(f"  {i + 1}/{len(tareas)} corridas ({time.perf_counter() - t0:.0f} s)", flush=True)
    with open(salida_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    if salida_npz is not None and (curvas or divs):
        np.savez_compressed(salida_npz, **curvas, **divs)
    print(f"{salida_csv.name}: {len(filas)} corridas en {time.perf_counter() - t0:.0f} s", flush=True)
    return filas


def semillas(n: int) -> list:
    return [SEMILLA_BASE + i for i in range(n)]
