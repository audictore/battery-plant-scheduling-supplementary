"""Taller híbrido de la planta de baterías: máquinas paralelas por etapa, re-entradas y cambios entre familias en el recocido.
Los datos son los de Ma et al. (Mendeley Data, doi:10.17632/x9sssz7jy4.1, CC BY 4.0) transcritos en instancias/baterias_parametros.json.
Todos los tiempos se manejan en décimas de hora (enteros). Ver la regla de decodificación en nucleo.cpp (Decoder::run_hfs)."""
from __future__ import annotations

import ctypes
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .nucleo import CRUZA, CRUZA_BASE, ENC, Config, _cargar

JSON = Path(__file__).resolve().parents[1] / "instancias" / "baterias_parametros.json"
ETAPA_SEQ = 3            # el recocido (4.ª etapa) es la que tiene cambio dependiente de la secuencia


@dataclass(frozen=True)
class InstanciaHFS:
    nombre: str
    trabajos: tuple          # por orden: tuple de (etapa, proceso, preparación fija) en décimas de hora, en el orden de su ruta
    familias: tuple          # familia (0 a 3) de cada orden
    maquinas: tuple          # máquinas paralelas de cada etapa
    cambio: tuple            # matriz familia a familia (décimas de hora) del recocido
    etapa_seq: int = ETAPA_SEQ

    @property
    def n_ordenes(self) -> int:
        return len(self.trabajos)

    @property
    def n_operaciones(self) -> int:
        return sum(len(t) for t in self.trabajos)


def _d(x: float) -> int:
    return int(round(10 * x))


def cargar_baterias(ruta: Path = JSON) -> dict:
    """{'bat_G1': InstanciaHFS, ..., 'bat_G5': ...}. G1 sale de la lista de lotes de la tabla A.4; G2 a G5, de los conteos por ruta (tabla A.6)."""
    d = json.loads(Path(ruta).read_text(encoding="utf-8"))
    etapas = d["etapas"]
    maquinas = tuple(e["maquinas"] for e in etapas)
    cambio = tuple(tuple(_d(x) for x in fila) for fila in d["cambio_recocido"])

    def trabajo(ruta_id: str):
        r = d["rutas"][ruta_id]
        fam = int(r["familia"][1]) - 1
        ops = []
        for j, _capa in r["ops"]:
            e = etapas[j - 1]
            p = d["recocido_por_familia"][r["familia"]] if e["p"] is None else e["p"]
            ops.append((j - 1, _d(p), _d(e["s"])))
        return tuple(ops), fam

    def armar(nombre: str, rutas: list) -> InstanciaHFS:
        tj = [trabajo(r) for r in rutas]
        return InstanciaHFS(nombre, tuple(t for t, _ in tj), tuple(f for _, f in tj), maquinas, cambio)

    out = {"bat_G1": armar("bat_G1", [j["ruta"] for j in d["G1_trabajos"]])}
    for g in ("G2", "G3", "G4", "G5"):
        rutas = []
        for ruta_id in sorted(d["conteo_rutas"][g], key=lambda x: int(x[4:])):
            rutas += [ruta_id] * d["conteo_rutas"][g][ruta_id]
        out["bat_" + g] = armar("bat_" + g, rutas)
    return out


def variante(grupo: str, semilla: int, ruta: Path = JSON) -> InstanciaHFS:
    """Variante de un grupo: mismos lotes y composición por familia que el grupo (tabla A.5), con la ruta de cada lote elegida al azar entre las de su
    familia. No es del conjunto original: es una extensión con sus mismas reglas, para tener más instancias."""
    d = json.loads(Path(ruta).read_text(encoding="utf-8"))
    rng = np.random.default_rng(semilla)
    por_familia = {}
    for rid, r in d["rutas"].items():
        por_familia.setdefault(r["familia"], []).append(rid)
    rutas = []
    for i, cuantos in enumerate(d["grupos"][grupo]["familias"]):
        opciones = sorted(por_familia[f"F{i + 1}"], key=lambda x: int(x[4:]))
        rutas += [opciones[k] for k in sorted(rng.integers(0, len(opciones), size=cuantos))]
    base = cargar_baterias(ruta)["bat_" + grupo]
    maquinas, cambio = base.maquinas, base.cambio
    etapas = d["etapas"]
    tj = []
    for rid in rutas:
        r = d["rutas"][rid]
        ops = tuple((j - 1, _d(d["recocido_por_familia"][r["familia"]] if etapas[j - 1]["p"] is None else etapas[j - 1]["p"]), _d(etapas[j - 1]["s"])) for j, _ in r["ops"])
        tj.append((ops, int(r["familia"][1]) - 1))
    return InstanciaHFS(f"bat_{grupo}v", tuple(t for t, _ in tj), tuple(f for _, f in tj), maquinas, cambio)


def instancia_bat(nombre: str):
    """'bat_G3' (la del conjunto), 'bat_G3v2' (variante de evaluación 2), 'bat_G3t1' (variante de ajuste 1); con '#n' al final, el modo de decodificación n.
    Devuelve (InstanciaHFS, modo)."""
    base, _, modo = nombre.partition("#")
    m = re.fullmatch(r"bat_(G[1-5])(?:([vt])(\d+))?", base)
    if not m:
        raise KeyError(nombre)
    g, tipo, k = m.group(1), m.group(2), m.group(3)
    if tipo is None:
        inst = cargar_baterias()[base]
    else:
        semilla = (2000 if tipo == "v" else 7000) + 10 * int(g[1]) + int(k)
        inst = variante(g, semilla)
        inst = InstanciaHFS(base, inst.trabajos, inst.familias, inst.maquinas, inst.cambio)
    return inst, int(modo or 0)


class ProblemaHFS:
    """Arreglos planos de una instancia del taller híbrido, listos para el núcleo. Misma interfaz que `Problema` (ejecutar, decodificar)."""

    def __init__(self, inst: InstanciaHFS, modo: int = 0):
        self.inst = inst
        self.modo = modo
        self.len = np.array([len(t) for t in inst.trabajos], dtype=np.int32)
        ops = [o for t in inst.trabajos for o in t]
        self.stage = np.array([o[0] for o in ops], dtype=np.int32)
        self.pt = np.array([o[1] for o in ops], dtype=np.int32)
        self.setup = np.array([o[2] for o in ops], dtype=np.int32)
        self.fam = np.array(inst.familias, dtype=np.int32)
        self.nm = np.array(inst.maquinas, dtype=np.int32)
        self.su = np.array([x for fila in inst.cambio for x in fila], dtype=np.int32)
        self.N = int(self.len.sum())

    def _ptrs(self):
        c = lambda a: a.ctypes.data_as(ctypes.POINTER(ctypes.c_int))
        return (self.inst.n_ordenes, len(self.nm), c(self.len), c(self.stage), c(self.pt), c(self.setup), c(self.fam), c(self.nm), c(self.su),
                len(self.inst.cambio), self.inst.etapa_seq, self.modo)

    def decodificar(self, prio, con_detalle: bool = False):
        """Makespan de un vector de prioridades (décimas de hora); con `con_detalle` devuelve también (inicio del proceso, máquina) de cada operación."""
        lib = _cargar()
        prio = np.ascontiguousarray(prio, dtype=np.float64)
        ini = np.zeros(self.N, dtype=np.int32) if con_detalle else None
        maq = np.zeros(self.N, dtype=np.int32) if con_detalle else None
        mk = lib.jsp_decodificar_hfs(*self._ptrs(), prio.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
                                     ini.ctypes.data_as(ctypes.POINTER(ctypes.c_int)) if con_detalle else None,
                                     maq.ctypes.data_as(ctypes.POINTER(ctypes.c_int)) if con_detalle else None)
        return (mk, ini, maq) if con_detalle else mk

    def ejecutar(self, codificacion: str, semilla: int, cfg: Config = Config(), diversidad: bool = False) -> dict:
        lib = _cargar()
        enc = ENC[codificacion]
        cruza = 0
        if codificacion != "aleatoria":
            cruza = CRUZA[codificacion][cfg.cruza or CRUZA_BASE[codificacion]]
        curva = np.zeros(cfg.gens + 1, dtype=np.int32)
        div = np.zeros(cfg.gens + 1, dtype=np.float64) if diversidad else None
        prio = np.zeros(self.N, dtype=np.float64)
        evals = ctypes.c_longlong(0)
        mejor = lib.jsp_ejecutar_hfs(*self._ptrs(), enc, cruza, int(cfg.gray), cfg.bits, cfg.pop, cfg.gens, cfg.elite, cfg.torneo, cfg.pc,
                                     cfg.escala_mutacion, cfg.sigma, ctypes.c_uint64(semilla), curva.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
                                     div.ctypes.data_as(ctypes.POINTER(ctypes.c_double)) if diversidad else None,
                                     prio.ctypes.data_as(ctypes.POINTER(ctypes.c_double)), ctypes.byref(evals))
        return {"mejor": int(mejor), "curva": curva, "diversidad": div, "prio": prio, "evaluaciones": int(evals.value)}


# --- verificación independiente (sin el núcleo) -------------------------------------------------------------------------------------------
def decodificar_py(inst: InstanciaHFS, prio, modo: int = 0):
    """La misma regla de decodificación escrita aparte en Python (con los modos de nucleo.cpp). Devuelve (makespan, inicio del proceso, máquina)."""
    n = inst.n_ordenes
    offs = np.concatenate([[0], np.cumsum([len(t) for t in inst.trabajos])])
    moff = np.concatenate([[0], np.cumsum(inst.maquinas)])
    sig = [0] * n
    listo = [0] * n
    libre = [0] * int(moff[-1])
    ultima = [-1] * int(moff[-1])
    ini = np.zeros(int(offs[-1]), dtype=np.int64)
    maq = np.zeros(int(offs[-1]), dtype=np.int64)
    mk = 0
    for _ in range(int(offs[-1])):
        cand = [(prio[offs[j] + sig[j]], offs[j] + sig[j], j) for j in range(n) if sig[j] < len(inst.trabajos[j])]
        _, o, j = min(cand)
        et, p, s_fija = inst.trabajos[j][sig[j]]
        mejor = None
        for mi in range(inst.maquinas[et]):
            m = int(moff[et]) + mi
            s = inst.cambio[ultima[m]][inst.familias[j]] + (s_fija if modo & 1 else 0) if (et == inst.etapa_seq and ultima[m] >= 0) else s_fija
            comienzo = max(libre[m] + s, listo[j]) if modo & 2 else max(listo[j], libre[m]) + s
            fin = comienzo + p
            if mejor is None or fin < mejor[0]:
                mejor = (fin, m, comienzo)
        fin, m, comienzo = mejor
        ini[o], maq[o] = comienzo, m
        listo[j] = libre[m] = fin
        ultima[m] = inst.familias[j]
        sig[j] += 1
        mk = max(mk, fin)
    return mk, ini, maq


def comprobar(inst: InstanciaHFS, inicios, maquinas, modo: int = 0) -> int:
    """Verifica un calendario (inicio del proceso y máquina de cada operación) y devuelve su makespan. AssertionError si una orden rompe su ruta, si una
    operación usa una máquina de otra etapa o si dos bloques (preparación + proceso) se solapan en una máquina. La preparación de cada operación es la
    que corresponde a la operación anterior de su máquina: la de la matriz en el recocido y la fija en los demás casos y en la primera operación."""
    offs = np.concatenate([[0], np.cumsum([len(t) for t in inst.trabajos])])
    moff = np.concatenate([[0], np.cumsum(inst.maquinas)])
    por_maquina = {}
    for j, t in enumerate(inst.trabajos):
        for k, (et, p, s) in enumerate(t):
            o = int(offs[j]) + k
            assert moff[et] <= maquinas[o] < moff[et + 1], f"operación {o}: máquina {maquinas[o]} fuera de la etapa {et}"
            por_maquina.setdefault(int(maquinas[o]), []).append((int(inicios[o]), o, j, k))
    prep, fin = {}, {}
    for m, lista in por_maquina.items():
        lista.sort()
        ultima = None
        for ini, o, j, k in lista:
            et, p, s_fija = inst.trabajos[j][k]
            s = inst.cambio[inst.familias[ultima]][inst.familias[j]] + (s_fija if modo & 1 else 0) if (et == inst.etapa_seq and ultima is not None) else s_fija
            prep[o], fin[o] = s, ini + p
            ultima = j
    for m, lista in por_maquina.items():
        for (i0, o0, _, _), (i1, o1, _, _) in zip(lista, lista[1:]):
            assert i1 - prep[o1] >= fin[o0], f"máquina {m}: los bloques de las operaciones {o0} y {o1} se solapan"
    for j, t in enumerate(inst.trabajos):
        for k in range(1, len(t)):
            o = int(offs[j]) + k
            assert inicios[o] - (0 if modo & 2 else prep[o]) >= fin[o - 1], f"orden {j}: la operación {k} empieza antes de terminar la anterior"
    return int(max(fin.values()))


def cota_capacidad(inst: InstanciaHFS, modo: int = 0) -> int:
    """Cota inferior del makespan por capacidad del recocido (décimas de hora): cada operación del recocido ocupa una de sus máquinas al menos proceso +
    la menor preparación posible; esa carga, repartida entre las máquinas, no puede empezar antes de lo que tardan en llegar al recocido el lote más rápido
    (salvo que la preparación se adelante, modo 2) y debe dejar después, como mínimo, lo que le falta al lote con menos trabajo posterior."""
    e = inst.etapa_seq
    fijas = min(o[2] for t in inst.trabajos for o in t if o[0] == e)
    prep_min = fijas if modo & 1 else min(min(min(f) for f in inst.cambio), fijas)
    carga = sum(o[1] + prep_min for t in inst.trabajos for o in t if o[0] == e)
    cabeza = 0 if modo & 2 else min(sum(o[1] + o[2] for o in t[:next(k for k, o in enumerate(t) if o[0] == e)]) for t in inst.trabajos)
    cola = min(sum(o[1] + o[2] for o in t[max(k for k, o in enumerate(t) if o[0] == e) + 1:]) for t in inst.trabajos)
    return cabeza + -(-carga // inst.maquinas[e]) + cola
