"""Figuras del artículo de la planta de baterías (300 dpi, 8.5 pt como el resto del estilo): esquema de la planta, Gantt del calendario de G1,
brechas por instancia, presupuesto de evaluaciones y sensibilidad a los supuestos."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import estilo as E

BASE = Path(__file__).resolve().parents[1]
FIG = BASE.parent / "manuscrito" / "figuras"
COLOR = {"binaria": E.ORDEN[0], "permutacion": E.ORDEN[1], "llaves": E.ORDEN[2], "aleatoria": E.TENUE}
MARCA = {"binaria": "o", "permutacion": "s", "llaves": "^", "aleatoria": "D"}
NOMBRE = {"binaria": "Binaria", "permutacion": "Permutación", "llaves": "Llaves", "aleatoria": "Aleatoria"}


def _tinta(hexa: str) -> str:
    r, g, b = (int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    lum = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    return "white" if 1.05 / (lum + 0.05) >= (lum + 0.05) / 0.05 else E.TINTA


def fig_planta(ruta) -> None:
    """Esquema: siete etapas con sus máquinas, y las re-entradas del recocido a la laminación en frío."""
    E.aplicar()
    d = json.loads((BASE / "instancias" / "baterias_parametros.json").read_text(encoding="utf-8"))
    et = d["etapas"]
    nombres = ["Fusión", "Colada y\nlaminación", "Laminación\nen frío", "Recocido\n(cuello)", "Corte", "Pulido", "Empaque"]
    fig, ax = E.plt.subplots(figsize=(E.ANCHO, 2.3))
    paso, w, h = 1.62, 1.3, 1.15
    ax.set_xlim(-0.1, 6 * paso + w + 0.1)
    ax.set_ylim(-1.85, 1.2)
    ax.axis("off")
    for i, (e, n) in enumerate(zip(et, nombres)):
        x = i * paso
        cuello = i == 3
        ax.add_patch(E.plt.Rectangle((x, -h / 2), w, h, facecolor=E.ORDEN[1] if cuello else "#eceae3", edgecolor=E.TINTA2, linewidth=0.8, zorder=2))
        ax.text(x + w / 2, 0.24, n, ha="center", va="center", fontsize=7.2, color=E.TINTA, zorder=3, linespacing=0.95)
        p = "7.6 a 8.8 h" if e["p"] is None else f"{e['p']:.1f} h"
        ax.text(x + w / 2, -0.2, f"{e['maquinas']} máquina" + ("s" if e["maquinas"] > 1 else ""), ha="center", va="center", fontsize=6.4, color=E.TINTA2 if not cuello else E.TINTA, zorder=3)
        ax.text(x + w / 2, -0.42, p, ha="center", va="center", fontsize=6.4, color=E.TINTA2 if not cuello else E.TINTA, zorder=3)
        if i < 6:
            ax.annotate("", xy=(x + paso - 0.02, 0), xytext=(x + w + 0.02, 0), arrowprops=dict(arrowstyle="-|>", color=E.TINTA2, lw=0.9), zorder=1)
    x3, x2 = 3 * paso + w * 0.35, 2 * paso + w * 0.65
    ax.annotate("", xy=(x2, -h / 2 - 0.03), xytext=(x3, -h / 2 - 0.03), arrowprops=dict(arrowstyle="-|>", color=E.ORDEN[1], lw=1.3, connectionstyle="arc3,rad=-0.6"), zorder=1)
    ax.text((x2 + x3) / 2, -1.35, "hasta 3 re-entradas\nsegún la familia", ha="center", va="center", fontsize=6.8, color=E.TINTA2)
    ax.text(3 * paso + w / 2, 0.88, "cambio entre familias: 1.5 a 3.0 h", ha="center", va="center", fontsize=6.6, color=E.TINTA2)
    E.guardar(fig, ruta)


def bloques(inst, inicios, maquinas, modo: int = 0):
    """Por operación: (máquina, inicio de la preparación, inicio del proceso, fin, orden, posición, preparación)."""
    offs = np.concatenate([[0], np.cumsum([len(t) for t in inst.trabajos])])
    por = {}
    for j, t in enumerate(inst.trabajos):
        for k, _ in enumerate(t):
            por.setdefault(int(maquinas[offs[j] + k]), []).append((int(inicios[offs[j] + k]), j, k))
    out = []
    for m, lista in por.items():
        lista.sort()
        ultima = None
        for ini, j, k in lista:
            et, p, s_fija = inst.trabajos[j][k]
            s = inst.cambio[inst.familias[ultima]][inst.familias[j]] + (s_fija if modo & 1 else 0) if (et == inst.etapa_seq and ultima is not None) else s_fija
            out.append((m, ini - s, ini, ini + p, j, k, s))
            ultima = j
    return out


NOMBRES_ETAPA = ["Fusión", "Colada", "Lam. frío", "Recocido", "Corte", "Pulido", "Empaque"]


def fig_gantt(ruta, inst, calendarios: list, titulos: list, limite: float, modo: int = 0, ancho: float = E.COL) -> None:
    """Gantt de uno o varios calendarios de la misma instancia, una fila por máquina; cada lote (orden) lleva su color y su número, y la preparación
    va como barra gris rayada antes de cada proceso."""
    E.aplicar()
    nm = int(sum(inst.maquinas))
    moff = np.concatenate([[0], np.cumsum(inst.maquinas)])
    etiquetas = []
    for e, q in enumerate(inst.maquinas):
        etiquetas += [f"{NOMBRES_ETAPA[e]} {i + 1}" if q > 1 else NOMBRES_ETAPA[e] for i in range(q)]
    n = len(calendarios)
    angosto = ancho < 5
    fig, ejes = E.plt.subplots(n, 1, figsize=(ancho, (2.35 if angosto else 2.55) * n + 0.55), constrained_layout=True, sharex=True)
    ejes = np.atleast_1d(ejes)
    paso_x = 200 if angosto else 100
    for ax, (ini, maq), titulo in zip(ejes, calendarios, titulos):
        bl = bloques(inst, ini, maq, modo)
        for m, s0, s1, e1, j, k, s in bl:
            y = nm - 1 - m
            ax.barh(y, s1 - s0, left=s0, height=0.78, color="#d9d8d0", edgecolor="white", linewidth=0.3, hatch="////", zorder=2)
            c = E.ORDENES[j]
            ax.barh(y, e1 - s1, left=s1, height=0.78, color=c, edgecolor="white", linewidth=0.4, zorder=3)
            if (e1 - s1) >= (20 if angosto else 12):
                ax.text((s1 + e1) / 2, y, str(j + 1), ha="center", va="center", fontsize=4.2 if angosto else 4.8, color=_tinta(c), zorder=4, clip_on=True)
        mk = max(b[3] for b in bl)
        ax.axvline(mk, color=E.TINTA2, lw=0.8, ls="--", zorder=1)
        ax.text(mk, nm - 0.3, f"{mk / 10:.1f} h", ha="right", va="bottom", fontsize=7, color=E.TINTA)
        for e in range(1, len(inst.maquinas)):
            ax.axhline(nm - 1 - moff[e] + 0.5, color=E.REJILLA, lw=0.6, zorder=0)
        ax.set_yticks(range(nm))
        ax.set_yticklabels(list(reversed(etiquetas)), fontsize=5.6 if angosto else 6.3)
        ax.set_ylim(-0.6, nm - 0.05)
        ax.set_xlim(0, limite)
        ax.grid(axis="y", visible=False)
        ax.set_xticks(np.arange(0, limite + 1, paso_x))
        ax.set_xticklabels([f"{int(x / 10)}" for x in np.arange(0, limite + 1, paso_x)])
        E.letra(ax, titulo)
    ejes[-1].set_xlabel("Tiempo desde el inicio (h)")
    nj = inst.n_ordenes
    asas = [E.plt.Rectangle((0, 0), 1, 1, facecolor=E.ORDENES[j], edgecolor="none") for j in range(nj)] + [E.plt.Rectangle((0, 0), 1, 1, facecolor="#d9d8d0", hatch="////", edgecolor="white")]
    fig.legend(asas, [f"B{j + 1}" for j in range(nj)] + ["Preparación"], loc="outside lower center", ncol=6 if angosto else nj + 1, fontsize=6.0 if angosto else 6.5, handlelength=1.0,
               handleheight=0.9, columnspacing=0.8, handletextpad=0.4)
    E.guardar(fig, ruta)
