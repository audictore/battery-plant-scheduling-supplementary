"""Tablas LaTeX (manuscrito/tablas/) y cifras del texto (manuscrito/numeros.tex) del artículo de la planta de baterías, generadas desde los CSV.
Cada cifra del texto sale de aquí (macros \\n...) para que no haya transcripciones a mano. Uso: python3 -m analisis_jsp.tablas_bat"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from . import bat
from . import estadistica as est
from .bat import GRUPOS, METODOS, NOMBRE, RES, TODOS

MAN = Path(__file__).resolve().parents[2] / "manuscrito"
SAL = MAN / "tablas"
CORTO = {"aleatoria": "Aleat.", "binaria": "Binaria", "llaves": "Llaves", "permutacion": "Perm.", "MOPNR": "MOPNR"}
NUM: dict = {}


def f(x, d=1) -> str:
    return f"{x:.{d}f}"


def pexp(p: float) -> str:
    """Valor p en forma de LaTeX matemático: 0.0013 o 3.0\\times10^{-7}."""
    if p >= 1e-3:
        return f"{p:.2g}" if p >= 0.01 else f"{p:.4f}".rstrip("0")
    m, e = f"{p:.1e}".split("e")
    return f"{m}\\times10^{{{int(e)}}}"


def num(nombre: str, valor, d=1) -> None:
    """Registra la macro \\n<nombre> con el valor formateado (texto ya listo si es str)."""
    NUM[nombre] = valor if isinstance(valor, str) else f(valor, d)


def tabular(spec: str, cab: str, filas: list, pre: str = r"\scriptsize\setlength{\tabcolsep}{2.5pt}") -> str:
    return pre + "\n\\begin{tabular}{" + spec + "}\n\\toprule\n" + cab + " \\\\\n\\midrule\n" + "\n".join(filas) + "\n\\bottomrule\n\\end{tabular}\n"


def escribir(nombre: str, texto: str) -> None:
    SAL.mkdir(parents=True, exist_ok=True)
    (SAL / f"{nombre}.tex").write_text(texto, encoding="utf-8")


def _existe(*n) -> bool:
    return all((RES / x).exists() for x in n)


def cargar():
    r = bat.referencias()
    out = {"ref": r}
    for clave, archivo in (("b1", "B1_base.csv"), ("b2b", "B2b_ajustado.csv"), ("b3", "B3_operadores.csv"), ("b6", "B6_supuestos.csv")):
        if _existe(archivo):
            out[clave] = pd.read_csv(RES / archivo)
    if _existe("B5_reglas.csv"):
        out["b5"] = pd.read_csv(RES / "B5_reglas.csv")
    return out


def brechas(d: pd.DataFrame, ref: pd.Series) -> pd.DataFrame:
    return bat.con_brecha(d, ref)


def por_tamano(m: pd.Series | pd.DataFrame):
    """Media por grupo de tamaño (G1..G5) de una serie/columnas indexadas por instancia."""
    idx = pd.Series([bat.tamano(i) for i in m.index], index=m.index)
    return m.groupby(idx).mean()


def regla_mopnr(x, ref):
    b = x["b5"]
    b = b[(b["modo"] == 0) & (b["regla"] == "MOPNR")].set_index("instancia")["makespan"]
    return 100 * (b - ref) / ref


def tabla_originales(x) -> str:
    """Una columna por instancia original y una fila por concepto (cota, mejor conocido, MOPNR y la mediana de cada método con parámetros base)."""
    from jsp_ag.hfs import instancia_bat
    r = x["ref"]
    med = x["b1"].groupby(["instancia", "metodo"])["mejor"].median().unstack()
    reg = x["b5"][(x["b5"]["modo"] == 0)].pivot(index="instancia", columns="regla", values="makespan")
    inst = [f"bat_{g}" for g in GRUPOS]
    cab = "Tiempo total (h) & " + " & ".join(f"{g} ({instancia_bat(f'bat_{g}')[0].n_operaciones})" for g in GRUPOS)
    filas = [("Cota inferior", [r.loc[i, "cota"] for i in inst]), ("Mejor conocido (MVC)", [r.loc[i, "mvc"] for i in inst]), ("Regla MOPNR", [reg.loc[i, "MOPNR"] for i in inst]),
             ("Binaria (mediana)", [med.loc[i, "binaria"] for i in inst]), ("Permutación (mediana)", [med.loc[i, "permutacion"] for i in inst]),
             ("Llaves (mediana)", [med.loc[i, "llaves"] for i in inst]), ("Aleatoria (mediana)", [med.loc[i, "aleatoria"] for i in inst])]
    cuerpo = []
    for n, (nombre, v) in enumerate(filas):
        cuerpo.append(f"{nombre} & " + " & ".join(f(a / 10) for a in v) + " \\\\")
        if n in (1, 2):
            cuerpo.append("\\midrule")
    return tabular(r"@{}l r r r r r@{}", cab, cuerpo)


def resumen_b1(x):
    r = x["ref"]
    d = brechas(x["b1"], r["mvc"])
    M = bat.medianas(d, ["metodo"])
    M["MOPNR"] = regla_mopnr(x, r["mvc"])
    return d, M


def tabla_agregada(x) -> str:
    d, M = resumen_b1(x)
    cols = TODOS + ["MOPNR"]
    t = por_tamano(M[cols])
    filas = [f"{g} (5 instancias) & " + " & ".join(f(t.loc[g, c]) for c in cols) + " \\\\" for g in GRUPOS]
    filas.append("\\midrule")
    filas.append("Las 25, parámetros base & " + " & ".join(f(M[c].mean()) for c in cols) + " \\\\")
    rang = est.friedman(M[METODOS + ["aleatoria"]].to_numpy())
    rr = dict(zip(METODOS + ["aleatoria"], rang[2]))
    filas.append("Rango medio de Friedman (base) & " + " & ".join(f(rr[c], 2) if c in rr else "--" for c in cols) + " \\\\")
    for clave, nombre in (("b2b", "Las 25, ajustados en la planta"),):
        if clave in x:
            Mx = bat.medianas(brechas(x[clave], x["ref"]["mvc"]), ["metodo"])
            filas.append(f"{nombre} & " + " & ".join(f(Mx[c].mean()) for c in METODOS) + " & -- & -- \\\\")
    cab = "Instancias & " + " & ".join(f"\\shortstack[r]{{{CORTO[c]}}}" for c in cols)
    return tabular(r"@{}l r r r r r@{}", cab, filas)


def cifras_b1(x) -> None:
    d, M = resumen_b1(x)
    r = x["ref"]
    for c in TODOS:
        num(f"gap{c.capitalize()}", M[c].mean(), 1)
    num("gapMOPNR", M["MOPNR"].mean(), 1)
    chi, p, rg = bat.friedman_rangos(M[TODOS])
    num("friedmanChi", chi, 1)
    num("friedmanP", "p<10^{-14}" if p < 1e-14 else f"p={p:.2g}")
    pares = [("permutacion", "llaves"), ("permutacion", "binaria"), ("llaves", "binaria"), ("llaves", "aleatoria"), ("binaria", "aleatoria")]
    for (a, b), fila in zip(pares, bat.holm_pares(M, pares)):
        num(f"holm_{a[:4]}_{b[:4]}", f"{fila[8]:.1e}".replace("e-0", "\\times10^{-").replace("e-", "\\times10^{-") + "}")
        num(f"gana_{a[:4]}_{b[:4]}", str(fila[4]))
    # horas por encima del MVC en las originales y de la cota
    orig = [f"bat_{g}" for g in GRUPOS]
    num("cotaMvcMin", (100 * (r.loc[orig, "mvc"] - r.loc[orig, "cota"]) / r.loc[orig, "cota"]).min(), 1)
    num("cotaMvcMax", (100 * (r.loc[orig, "mvc"] - r.loc[orig, "cota"]) / r.loc[orig, "cota"]).max(), 1)
    # Mann-Whitney por instancia (permutación vs llaves) con Holm
    ps = []
    for i in r.index:
        u = x["b1"].query("instancia==@i and metodo=='permutacion'")["mejor"].to_numpy()
        v = x["b1"].query("instancia==@i and metodo=='llaves'")["mejor"].to_numpy()
        ps.append(est.mann_whitney(u, v)[1])
    ph = est.holm(ps)
    num("mwSignif", str(int((ph < 0.05).sum())))
    num("a12Perm", np.mean([est.a12(x["b1"].query("instancia==@i and metodo=='permutacion'")["mejor"], x["b1"].query("instancia==@i and metodo=='llaves'")["mejor"]) for i in r.index]), 2)
    # horas ahorradas frente a MOPNR y a la búsqueda aleatoria (medianas, en horas), por grupo
    med = x["b1"].groupby(["instancia", "metodo"])["mejor"].median().unstack()
    reg = x["b5"][(x["b5"]["modo"] == 0) & (x["b5"]["regla"] == "MOPNR")].set_index("instancia")["makespan"]
    ah = (reg - med["permutacion"]) / 10
    for g in GRUPOS:
        num(f"ahorro{g}", ah[f"bat_{g}"], 1)
    num("ahorroMin", ah.min(), 1)
    num("ahorroMax", ah.max(), 1)
    num("ahorroPct", (100 * (reg - med["permutacion"]) / reg).mean(), 1)
    rg = x["b5"][x["b5"]["modo"] == 0].pivot(index="instancia", columns="regla", values="makespan")
    for regla in ("SPT", "MWKR", "MOPNR"):
        num(f"gap{regla}", (100 * (rg[regla] - r["mvc"].reindex(rg.index)) / r["mvc"].reindex(rg.index)).mean(), 1)
    num("mopnrMejorRegla", str(int((rg["MOPNR"] <= rg[["SPT", "MWKR"]].min(axis=1)).sum())))
    mopg = por_tamano(M["MOPNR"])
    for g in GRUPOS:
        num(f"mopnr{g}", mopg[g], 1)
    gg = por_tamano(M[METODOS])
    for g in GRUPOS:
        for c in METODOS:
            num(f"base{g}{c[:4].capitalize()}", gg.loc[g, c], 1)


def escribir_numeros() -> None:
    lineas = ["% Generado por analisis_jsp/tablas_bat.py; no editar a mano."]
    letras = str.maketrans("0123456789", "ABCDEFGHIJ")         # LaTeX no admite dígitos en los nombres de macros
    nombres = set()
    for k, v in NUM.items():
        nombre = "".join(c for c in k if c.isalnum()).translate(letras)
        assert nombre not in nombres, f"macro repetida: {nombre}"
        nombres.add(nombre)
        if any(c in v for c in "^<\\"):
            v = "\\ensuremath{" + v + "}"
        lineas.append("\\newcommand{\\n" + nombre + "}{" + v + "}")
    (MAN / "numeros.tex").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def generar() -> None:
    x = cargar()
    MAN_FIG = MAN / "figuras"
    if "b1" in x and "b5" in x:
        escribir("originales", tabla_originales(x))
        escribir("agregada", tabla_agregada(x))
        cifras_b1(x)
    cifras_b2(x)
    for nombre, fn in (("comunes", tabla_comunes), ("ajuste", tabla_ajuste), ("presupuesto", tabla_presupuesto), ("supuestos", tabla_supuestos), ("cruzas_propias", tabla_cruzas_propias), ("bits", tabla_bits), ("exacto", tabla_exacto)):
        s = fn(x) if nombre != "ajuste" else fn(x)
        if s:
            escribir(nombre, s)
    s, M = tabla_operadores(x)
    if s:
        escribir("operadores", s)
        cifras_b3(x, M)
    fig_presupuesto(x, MAN_FIG / "fig_presupuesto.png")
    if (RES / "B7_calendarios.json").exists():
        from . import figuras_bat as FB
        from . import horario_bat as H
        from jsp_ag.corridas import problema
        cal = H.calendarios_g1()
        inst = problema("bat_G1").inst
        mejor = cal[cal["mejor"]]
        mop = cal["MOPNR"]
        FB.fig_gantt(MAN_FIG / "fig_gantt.png", inst, [(mop["inicios"], mop["maquinas"]), (mejor["inicios"], mejor["maquinas"])],
                     ["(a) Regla MOPNR", "(b) Mejor calendario conocido"], max(mop["makespan"], mejor["makespan"]) + 30)
        escribir("secuencias", H.tabla_secuencias(inst, mejor))
        rs, rm = H.resumen(inst, mejor), H.resumen(inst, mop)
        num("horarioMejor", mejor["makespan"] / 10, 1)
        num("horarioMOPNR", mop["makespan"] / 10, 1)
        num("horarioAhorro", (mop["makespan"] - mejor["makespan"]) / 10, 1)
        num("horarioCambios", str(rs["cambios"]))
        num("horarioCambiosMOPNR", str(rm["cambios"]))
        num("horarioPrep", rs["prep_recocido_h"], 1)
        num("horarioPrepMOPNR", rm["prep_recocido_h"], 1)
        num("horarioOcup", " / ".join(f"{o:.0f}" for o in rs["ocupacion_pct"]))
        for etiqueta, c_ in (("", mejor), ("MOPNR", mop)):
            tt = H.tardanzas(inst, c_)
            tarde = [x for x in tt if x[4] > 0]
            num(f"horarioTarde{etiqueta}", str(len(tarde)))
            num(f"horarioRetraso{etiqueta}", sum(x[4] for x in tarde), 1)
            num(f"horarioRetrasoMax{etiqueta}", max(x[4] for x in tt), 1)
            num(f"horarioTardeLotes{etiqueta}", ", ".join(x[0] for x in tarde))
        num("horarioOrigen", {"AG": "algoritmo genético", "CPSAT_con_pista": "CP-SAT con pista", "CPSAT_sin_pista": "CP-SAT"}[cal["mejor"]])
        r = x["ref"].loc["bat_G1"]
        H.libro_excel(inst, mejor, RES / "horario_G1.xlsx", {"cota": r["cota"], "mopnr": mop["makespan"]})
    escribir_numeros()




# ---------------------------------------------------------------------------------------------------------------------------------------------
# B0: parámetros comunes
def tabla_comunes(x) -> str | None:
    """Valor de partida (torneo 3, elitismo 2, cruza 0.9, sigma 0.15) frente al elegido en B0 para cada codificación."""
    if not _existe("B0_mejor_config.json"):
        return None
    cfg = json.loads((RES / "B0_mejor_config.json").read_text(encoding="utf-8"))
    filas = []
    for met in METODOS:
        c = cfg[met]
        k = met[:4].capitalize()
        sig = f"{c['sigma']:g}" if met == "llaves" else "--"
        filas.append(f"{NOMBRE[met]} & {c['torneo']} & {c['elite']} & {c['pc']:g} & {sig} & {f(100 * (c['rel_partida'] - 1), 1)} & {f(100 * (c['rel_confirmacion'] - 1), 1)} \\\\")
        num(f"bcTorneo{k}", str(c["torneo"]))
        num(f"bcElite{k}", str(c["elite"]))
        num(f"bcCruza{k}", f"{c['pc']:g}")
        num(f"bcSigma{k}", f"{c['sigma']:g}")
        num(f"bcPartida{k}", 100 * (c["rel_partida"] - 1), 1)
        num(f"bcElegido{k}", 100 * (c["rel_confirmacion"] - 1), 1)
    cab = "Codificación & Torneo & Elitismo & Cruza & $\\sigma$ & \\shortstack[r]{Exceso de\\\\partida (\\%)} & \\shortstack[r]{Exceso del\\\\elegido (\\%)}"
    return tabular(r"@{}l r r r r r r@{}", cab, filas)


# ---------------------------------------------------------------------------------------------------------------------------------------------
# B2: parámetros
def tabla_ajuste(x) -> str | None:
    if not _existe("B2a_rejilla.csv", "B2_mejor_config.json"):
        return None
    g = pd.read_csv(RES / "B2a_rejilla.csv")
    m = g.groupby(["metodo", "instancia", "escala", "pop"])["mejor"].mean().reset_index()
    m["rel"] = m["mejor"] / m.groupby(["metodo", "instancia"])["mejor"].transform("min")
    s = m.groupby(["metodo", "escala", "pop"])["rel"].mean().reset_index()
    filas = []
    for met in METODOS:
        t = s[s["metodo"] == met]
        mejor = t.sort_values("rel").iloc[0]
        peor = t.sort_values("rel").iloc[-1]
        base = t[(t["escala"] == 1.0) & (t["pop"] == 100)].iloc[0]
        filas.append(f"{NOMBRE[met]} & {mejor['escala']:g} / {int(mejor['pop'])} & {f(100 * (mejor['rel'] - 1), 2)} & {f(100 * (base['rel'] - 1), 2)} & {f(100 * (peor['rel'] - 1), 1)} \\\\")
        num(f"excesoBase{met[:4].capitalize()}", 100 * (base["rel"] - 1), 1)
        num(f"excesoMejor{met[:4].capitalize()}", 100 * (mejor["rel"] - 1), 2)
        num(f"excesoPeor{met[:4].capitalize()}", 100 * (peor["rel"] - 1), 1)
        num(f"mejorEscala{met[:4]}", f"{mejor['escala']:g}")
        num(f"mejorPop{met[:4]}", str(int(mejor["pop"])))
    cab = "Codificación & \\shortstack[r]{Mejor celda\\\\(escala / pob.)} & \\shortstack[r]{Exceso\\\\(\\%)} & \\shortstack[r]{Base (1 / 100)\\\\exceso (\\%)} & \\shortstack[r]{Peor celda\\\\exceso (\\%)}"
    return tabular(r"@{}l r r r r@{}", cab, filas)


def cifras_b2(x) -> None:
    if "b2b" not in x:
        return
    r = x["ref"]
    base = bat.medianas(brechas(x["b1"], r["mvc"]), ["metodo"])
    aj = bat.medianas(brechas(x["b2b"], r["mvc"]), ["metodo"])
    for c in METODOS:
        num(f"ajustada{c[:4].capitalize()}", aj[c].mean(), 1)
    conj = pd.concat([aj[METODOS].add_prefix("aj_"), base[["aleatoria"]]], axis=1)
    chi, p, rg = bat.friedman_rangos(aj[METODOS])
    num("friedmanAjP", "p=" + pexp(p))
    pares = [("permutacion", "llaves"), ("permutacion", "binaria"), ("llaves", "binaria")]
    for (a, b), fila in zip(pares, bat.holm_pares(aj, pares)):
        num(f"holmAj_{a[:4]}_{b[:4]}", f"{fila[8]:.1e}".replace("e-0", "\\times10^{-").replace("e-", "\\times10^{-") + "}")
        num(f"ganaAj_{a[:4]}_{b[:4]}", str(fila[4]))
    for c in METODOS:                                        # ajustada contra base, en cada codificación
        w = bat.holm_pares(pd.DataFrame({"a": aj[c], "b": base[c]}), [("a", "b")])[0]
        num(f"mejoraAj{c[:4].capitalize()}", str(w[4]))
        num(f"pAj{c[:4].capitalize()}", f"{w[8]:.1e}".replace("e-0", "\\times10^{-").replace("e-", "\\times10^{-") + "}")
    # ¿el MOPNR sigue ganándole a alguna?
    mop = regla_mopnr(x, r["mvc"]).reindex(aj.index)
    for c in METODOS:
        num(f"ajMenorMOPNR{c[:4].capitalize()}", str(int((aj[c] < mop).sum())))
        num(f"baseMenorMOPNR{c[:4].capitalize()}", str(int((base[c] < mop).sum())))


# ---------------------------------------------------------------------------------------------------------------------------------------------
# B3: ablación de operadores
ETIQ = {("binaria", "dos_puntos", False): "Binaria, dos puntos (base)", ("binaria", "un_punto", False): "Binaria, un punto", ("binaria", "uniforme", False): "Binaria, uniforme",
        ("binaria", "dos_puntos", True): "Binaria, dos puntos + Gray", ("binaria", "un_punto", True): "Binaria, un punto + Gray", ("binaria", "uniforme", True): "Binaria, uniforme + Gray",
        ("permutacion", "pox", False): "Permutación, POX (base)", ("permutacion", "ox", False): "Permutación, OX generalizado", ("permutacion", "ppx", False): "Permutación, PPX",
        ("llaves", "uniforme", False): "Llaves, uniforme (base)", ("llaves", "dos_puntos", False): "Llaves, dos puntos", ("llaves", "aritmetica", False): "Llaves, aritmética"}


def tabla_operadores(x):
    if "b3" not in x:
        return None, None
    d = x["b3"].copy()
    d["cruza"] = d["cruza"].fillna("")
    d["gray"] = d["gray"].astype(str).str.lower().isin(["true", "1"])
    d["v"] = list(zip(d["metodo"], d["cruza"], d["gray"]))
    r = x["ref"]
    d = brechas(d, r["mvc"])
    M = bat.medianas(d, ["v"])
    M.columns = [ETIQ[c] for c in M.columns]
    chi, p, rg = bat.friedman_rangos(M)
    filas = []
    for v in ETIQ.values():
        filas.append(f"{v} & {f(M[v].mean(), 2)} & {f(rg[v], 2)} & {f(M[v].min(), 2)}--{f(M[v].max(), 1)} \\\\")
    cab = "Variante & \\shortstack[r]{Brecha\\\\media (\\%)} & \\shortstack[r]{Rango\\\\medio} & \\shortstack[r]{Rango de las\\\\25 (\\%)}"
    num("friedmanOpP", "p<10^{-9}" if p < 1e-9 else f"p={p:.2g}")
    num("friedmanOpChi", chi, 1)
    return tabular(r"@{}l r r r@{}", cab, filas), M


def comparaciones_operadores(M: pd.DataFrame):
    """Comparaciones planeadas entre variantes, con Holm. Devuelve filas formateadas y cifras."""
    E = ETIQ
    p = [("Binaria, dos puntos (base)", "Binaria, uniforme"), ("Binaria, dos puntos (base)", "Binaria, un punto"), ("Binaria, dos puntos (base)", "Binaria, dos puntos + Gray"),
         ("Permutación, POX (base)", "Permutación, OX generalizado"), ("Permutación, POX (base)", "Permutación, PPX"), ("Permutación, OX generalizado", "Permutación, PPX"),
         ("Llaves, uniforme (base)", "Llaves, dos puntos"), ("Llaves, uniforme (base)", "Llaves, aritmética"), ("Llaves, dos puntos", "Llaves, aritmética"),
         ("Permutación, POX (base)", "Llaves, uniforme (base)"), ("Llaves, uniforme (base)", "Binaria, uniforme"), ("Binaria, uniforme", "Binaria, dos puntos (base)")]
    return bat.holm_pares(M, p)


def cifras_b3(x, M) -> None:
    if M is None:
        return
    mejor = {c: M[[v for v in M.columns if v.startswith(c)]].mean().idxmin() for c in ("Binaria", "Permutación", "Llaves")}
    peor = {c: M[[v for v in M.columns if v.startswith(c)]].mean().idxmax() for c in ("Binaria", "Permutación", "Llaves")}
    for c in mejor:
        num(f"opMejor{c[:4]}", f(M[mejor[c]].mean(), 1))
        num(f"opPeor{c[:4]}", f(M[peor[c]].mean(), 1))
        num(f"opMejorNombre{c[:4]}", mejor[c])
        num(f"opPeorNombre{c[:4]}", peor[c])
    # el peor operador de la permutación frente al mejor de las otras dos
    ox = "Permutación, OX generalizado"                      # la permutación con la cruza intermedia, frente al mejor de las otras dos
    pr = bat.holm_pares(M, [(peor["Permutación"], mejor["Llaves"]), (peor["Permutación"], mejor["Binaria"]), (mejor["Llaves"], mejor["Binaria"]),
                            (ox, mejor["Llaves"]), (ox, mejor["Binaria"])])
    for tag, fila in zip(("pPeorLl", "pPeorBi", "llBi", "pOxLl", "pOxBi"), pr):
        num(f"op{tag}", f"{fila[8]:.2f}" if fila[8] >= 0.01 else f"{fila[8]:.1e}".replace("e-0", "\\times10^{-").replace("e-", "\\times10^{-") + "}")
        num(f"opGana{tag}", str(fila[4]))
        num(f"opPierde{tag}", str(fila[6]))
    for i, fila in enumerate(comparaciones_operadores(M)):
        num(f"opHolm{i}", f"{fila[8]:.2g}")
        num(f"opGana{i}", str(fila[4]))
        num(f"opEmp{i}", str(fila[5]))
        num(f"opPierde{i}", str(fila[6]))
        num(f"opMediaA{i}", f(fila[2], 2))
        num(f"opMediaB{i}", f(fila[3], 2))


# ---------------------------------------------------------------------------------------------------------------------------------------------
# B4: presupuesto
EV = 100 * (1 + np.arange(3000))           # malla común de evaluaciones (población 100): se remuestrean las curvas de cada método sobre ella
CHECK = (10000, 30000, 100000, 300000)


def curvas_b4():
    if not _existe("B4_curvas.npz"):
        return None
    z = np.load(RES / "B4_curvas.npz")
    tabla = pd.read_csv(RES / "B4_presupuesto.csv")
    elite = tabla.groupby("metodo")["elite"].first().to_dict()          # tras la generación i van 100 + (100 - élite) * i evaluaciones
    out = {}
    for k in z.keys():
        p = k.split("|")
        c = z[k].astype(float)
        idx = np.clip((EV - 100) // (100 - int(elite[p[2]])), 0, len(c) - 1).astype(int)
        out.setdefault((p[1], p[2]), []).append(c[idx])
    return {k: np.array(v) for k, v in out.items()}


def serie_b4(x):
    """DataFrame de brecha media (sobre las 5 originales, de la mediana de las semillas) por método y evaluaciones."""
    c = curvas_b4()
    if c is None:
        return None
    r = x["ref"]["mvc"]
    orig = [f"bat_{g}" for g in GRUPOS]
    out = {}
    for m in TODOS:
        out[m] = np.mean([100 * (np.median(c[(i, m)], axis=0) - r[i]) / r[i] for i in orig], axis=0)
    return pd.DataFrame(out, index=EV)


def tabla_presupuesto(x):
    c = curvas_b4()
    if c is None:
        return None
    r = x["ref"]["mvc"]
    orig = [f"bat_{g}" for g in GRUPOS]
    filas = []
    for e in CHECK:
        i = int(np.searchsorted(EV, e, side="right") - 1)
        M = pd.DataFrame({m: [100 * (np.median(c[(inst, m)][:, i]) - r[inst]) / r[inst] for inst in orig] for m in TODOS}, index=orig)
        fr = est.friedman(M[METODOS + ["aleatoria"]].to_numpy())
        rg = dict(zip(METODOS + ["aleatoria"], fr[2]))
        mejor_orden = " < ".join(NOMBRE[m][:4] + "." for m in sorted(METODOS, key=lambda m: M[m].mean()))
        filas.append(f"{e:,}".replace(",", "\\,") + " & " + " & ".join(f(M[m].mean()) for m in TODOS) + f" & {mejor_orden} \\\\")
        num(f"presP{e}", f"{fr[1]:.2g}")
        for m in TODOS:
            num(f"pres{e}{m[:4].capitalize()}", M[m].mean(), 1)
    mop = regla_mopnr(x, r)[orig].mean()
    num("presMOPNR", mop, 1)
    cab = "Evaluaciones & " + " & ".join(f"\\shortstack[r]{{{CORTO[m]}}}" for m in TODOS) + " & Orden (menor brecha primero)"
    return tabular(r"@{}r r r r r l@{}", cab, filas)


def fig_presupuesto(x, ruta) -> None:
    from . import estilo as E
    from .figuras_bat import COLOR, MARCA
    s = serie_b4(x)
    if s is None:
        return
    E.aplicar()
    fig, ax = E.plt.subplots(figsize=(E.COL, 2.55), constrained_layout=True)
    paso = 25
    for m in TODOS:
        ax.plot(s.index[::paso], s[m].to_numpy()[::paso], color=COLOR[m], lw=1.5, label={"binaria": "Binaria", "permutacion": "Permutación", "llaves": "Llaves", "aleatoria": "Aleatoria"}[m])
        ax.plot(CHECK, [s[m].iloc[int(np.searchsorted(EV, e, side="right") - 1)] for e in CHECK], ls="none", marker=MARCA[m], color=COLOR[m], markeredgecolor="white", markersize=5)
    mop = regla_mopnr(x, x["ref"]["mvc"])[[f"bat_{g}" for g in GRUPOS]].mean()
    E.referencia(ax, "h", mop, "MOPNR", lado="der")
    ax.set_xscale("log")
    ax.set_xlim(2000, 300000)
    ax.set_ylim(-1, 36)
    ax.set_xlabel("Evaluaciones del decodificador")
    ax.set_ylabel("Brecha media (%)")
    ax.set_xticks([3000, 10000, 30000, 100000, 300000])
    ax.set_xticklabels(["3 000", "10 000", "30 000", "100 000", "300 000"])
    ax.minorticks_off()
    E.leyenda_figura(fig, [ax], ncol=4)
    E.guardar(fig, ruta)


# ---------------------------------------------------------------------------------------------------------------------------------------------
# B6: supuestos
DESC = {0: "0 (base)", 1: "1 (cambio + fija)", 2: "2 (prep. adelantada)", 3: "3 (ambos)"}


def tabla_supuestos(x):
    if "b6" not in x:
        return None
    d = x["b6"].copy()
    d["modo"] = d["instancia"].str.split("#").str[1].astype(int)
    d["inst"] = d["instancia"].str.split("#").str[0]
    b1 = x["b1"][x["b1"]["instancia"].isin([f"bat_{g}" for g in GRUPOS])].copy()
    b1["modo"] = 0
    b1["inst"] = b1["instancia"]
    d = pd.concat([d, b1[d.columns.intersection(b1.columns)]])
    reglas = x["b5"][x["b5"]["inst" if "inst" in x["b5"] else "instancia"].isin([f"bat_{g}" for g in GRUPOS])] if "b5" in x else None
    filas = []
    for modo in range(4):
        z = d[d["modo"] == modo]
        mvc = z.groupby("inst")["mejor"].min()
        if reglas is not None:
            rm = reglas[(reglas["modo"] == modo) & (reglas["regla"] == "MOPNR")].set_index("instancia")["makespan"]
            mvc = np.minimum(mvc, rm.reindex(mvc.index))
        z = z.assign(gap=100 * (z["mejor"] - z["inst"].map(mvc)) / z["inst"].map(mvc))
        M = z.groupby(["inst", "metodo"])["gap"].median().unstack()[TODOS]
        mop = 100 * (rm.reindex(M.index) - mvc) / mvc
        fr = est.friedman(M[METODOS + ["aleatoria"]].to_numpy())
        rg = dict(zip(METODOS + ["aleatoria"], fr[2]))
        orden = " < ".join(NOMBRE[m][:4] + "." for m in sorted(METODOS, key=lambda m: rg[m]))
        filas.append(f"{DESC[modo]} & {f(mvc.mean() / 10)} & " + " & ".join(f(M[m].mean()) for m in TODOS) + f" & {f(mop.mean())} & {orden} \\\\")
        num(f"modoMvc{modo}", mvc.mean() / 10, 1)
        for m in TODOS:
            num(f"modo{modo}{m[:4].capitalize()}", M[m].mean(), 1)
        num(f"modo{modo}MOPNR", mop.mean(), 1)
        num(f"modoP{modo}", f"{fr[1]:.2g}")
        num(f"modoOrden{modo}", orden)
        num(f"modoRangoPerm{modo}", rg["permutacion"], 1)
    for tag, m in (("Perm", "permutacion"), ("Llav", "llaves"), ("Bina", "binaria")):
        v = [float(NUM[f"modo{k}{m[:4].capitalize()}"]) for k in range(4)]
        num(f"modo{tag}Min", min(v), 1)
        num(f"modo{tag}Max", max(v), 1)
    cab = "Modo & \\shortstack[r]{Mejor\\\\conocido (h)} & " + " & ".join(f"\\shortstack[r]{{{CORTO[m]}}}" for m in TODOS) + " & MOPNR & Orden"
    return tabular(r"@{}l r r r r r r l@{}", cab, filas)


# ---------------------------------------------------------------------------------------------------------------------------------------------
# B2d y B8: ajuste propio de cada cruza y resolución de la binaria
def _med_gap(d, ref):
    return bat.medianas(brechas(d, ref), ["metodo"] if "cruza" not in d else ["metodo", "cruza"])


def tabla_cruzas_propias(x):
    if not _existe("B2d_ajustado.csv", "B2d_mejor_config.json") or "b2b" not in x or "b3" not in x:
        return None
    r = x["ref"]["mvc"]
    cfg2 = json.loads((RES / "B2_mejor_config.json").read_text(encoding="utf-8"))
    cfgd = json.loads((RES / "B2d_mejor_config.json").read_text(encoding="utf-8"))
    b3 = x["b3"].copy()
    b3["cruza"] = b3["cruza"].fillna("")
    b3["gray"] = b3["gray"].astype(str).str.lower().isin(["true", "1"])
    b3 = b3[~b3["gray"]]
    base = bat.medianas(brechas(b3, r), ["metodo", "cruza"])
    b2b = x["b2b"].copy()
    b2b["cruza"] = {"binaria": "dos_puntos", "permutacion": "pox", "llaves": "uniforme"}[b2b["metodo"].iloc[0]] if False else b2b["metodo"].map({"binaria": "dos_puntos", "permutacion": "pox", "llaves": "uniforme"})
    b2d = pd.read_csv(RES / "B2d_ajustado.csv")
    aj = bat.medianas(brechas(pd.concat([b2b, b2d]), r), ["metodo", "cruza"])
    filas, cols = [], [("binaria", "dos_puntos"), ("binaria", "uniforme"), ("llaves", "uniforme"), ("llaves", "dos_puntos"), ("permutacion", "pox")]
    etiqueta = {("binaria", "dos_puntos"): "Binaria, dos puntos", ("binaria", "uniforme"): "Binaria, uniforme", ("llaves", "uniforme"): "Llaves, uniforme",
                ("llaves", "dos_puntos"): "Llaves, dos puntos", ("permutacion", "pox"): "Permutación, POX"}
    for c in cols:
        if c[0] == "permutacion":
            ce = cfg2["permutacion"]
        elif c[0] == "binaria" and c[1] == "dos_puntos":
            ce = cfg2["binaria"]
        elif c[0] == "llaves" and c[1] == "uniforme":
            ce = cfg2["llaves"]
        else:
            ce = cfgd[f"{c[0]}/{c[1]}"]
        filas.append(f"{etiqueta[c]} & {f(base[c].mean(), 2)} & {ce['escala']:g} / {ce['pop']} & {f(aj[c].mean(), 2)} \\\\")
        num(f"propia{c[0][:4].capitalize()}{c[1].replace('_', '')}", aj[c].mean(), 1)
    # rangos y comparación del mejor de la binaria con el mejor de las llaves, ajustados
    M = pd.DataFrame({etiqueta[c]: aj[c] for c in cols})
    chi, p, rg = bat.friedman_rangos(M)
    mb = min([("binaria", "dos_puntos"), ("binaria", "uniforme")], key=lambda c: aj[c].mean())
    ml = min([("llaves", "uniforme"), ("llaves", "dos_puntos")], key=lambda c: aj[c].mean())
    h = bat.holm_pares(M, [(etiqueta[ml], etiqueta[mb]), (etiqueta[("permutacion", "pox")], etiqueta[ml])])
    num("propiaLlBiP", pexp(h[0][8]))
    num("propiaLlBiGana", str(h[0][4]))
    num("propiaPeLlP", pexp(h[1][8]))
    num("propiaMejorBi", etiqueta[mb])
    num("propiaMejorLl", etiqueta[ml])
    num("propiaDifBiLl", abs(aj[mb].mean() - aj[ml].mean()), 1)
    cab = "Combinación & \\shortstack[r]{Base\\\\brecha (\\%)} & \\shortstack[r]{Mejor celda\\\\(escala / pob.)} & \\shortstack[r]{Ajustada\\\\brecha (\\%)}"
    return tabular(r"@{}l r r r@{}", cab, filas)


def tabla_bits(x):
    if not _existe("B8_bits.csv") or "b3" not in x:
        return None
    r = x["ref"]["mvc"]
    b8 = pd.read_csv(RES / "B8_bits.csv")
    b3 = x["b3"].copy()
    b3["cruza"] = b3["cruza"].fillna("")
    b3["gray"] = b3["gray"].astype(str).str.lower().isin(["true", "1"])
    b3 = b3[(b3["metodo"] == "binaria") & (~b3["gray"])].assign(bits=8)
    d = pd.concat([b8, b3])
    from jsp_ag.conjunto_bat import EVALUACION
    from jsp_ag.hfs import instancia_bat
    nop = np.mean([instancia_bat(i)[0].n_operaciones for i in EVALUACION])
    filas = []
    for bits in (4, 8, 12, 16):
        v = {c: bat.medianas(brechas(d[(d["cruza"] == c) & (d["bits"] == bits)], r), ["metodo"])["binaria"].mean() for c in ("dos_puntos", "uniforme")}
        parejas = 467 * 466 / 2 / 2 ** bits
        filas.append(f"{bits} & {2 ** bits:,}".replace(",", "\\,") + f" & {f(parejas, 0 if parejas >= 10 else 1)} & {f(v['dos_puntos'])} & {f(v['uniforme'])} \\\\")
        for c in v:
            num(f"bits{bits}{c.replace('_', '')}", v[c], 1)
    cab = "Bits & Prioridades & \\shortstack[r]{Parejas empatadas\\\\esperadas ($N=467$)} & \\shortstack[r]{Dos puntos\\\\brecha (\\%)} & \\shortstack[r]{Uniforme\\\\brecha (\\%)}"
    return tabular(r"@{}r r r r r@{}", cab, filas)


def tabla_exacto(x):
    if not _existe("B7_exacto.csv"):
        return None
    cp = pd.read_csv(RES / "B7_exacto.csv")
    r = x["ref"]
    filas = []
    for g in GRUPOS:
        i = f"bat_{g}"
        s = cp[(cp["instancia"] == i) & (cp["variante"] == "sin_pista")].iloc[0]
        c = cp[(cp["instancia"] == i) & (cp["variante"] == "con_pista")].iloc[0]
        filas.append(f"{g} & {f(s['makespan_pista'] / 10)} & {f(s['makespan'] / 10)} & {f(c['makespan'] / 10)} & {f(100 * (s['makespan'] - r.loc[i, 'mvc']) / r.loc[i, 'mvc'])} & {f(100 * (c['makespan'] - r.loc[i, 'mvc']) / r.loc[i, 'mvc'])} & {f(max(s['cota_cpsat'], c['cota_cpsat']) / 10)} & {f(s['cota_capacidad'] / 10)} \\\\")
        num(f"cpSin{g}", 100 * (s["makespan"] - r.loc[i, "mvc"]) / r.loc[i, "mvc"], 1)
        num(f"cpCon{g}", 100 * (c["makespan"] - r.loc[i, "mvc"]) / r.loc[i, "mvc"], 1)
        num(f"cpPista{g}", 100 * (s["makespan_pista"] - r.loc[i, "mvc"]) / r.loc[i, "mvc"], 1)
        num(f"cpEstadoSin{g}", s["estado"])
    g = cp.assign(i=cp["instancia"])
    for v, tag in (("sin_pista", "Sin"), ("con_pista", "Con")):
        z = g[g["variante"] == v]
        num(f"cp{tag}Media", np.mean([100 * (a - r.loc[i, "mvc"]) / r.loc[i, "mvc"] for i, a in zip(z["instancia"], z["makespan"])]), 1)
    z = g[g["variante"] == "sin_pista"]
    con = g[g["variante"] == "con_pista"]
    num("cpMejoraN", str(int((con["makespan"].to_numpy() < z["makespan_pista"].to_numpy()).sum())))        # instancias en que CP-SAT mejoró la pista
    num("cpCotaMax", max(cp["cota_cpsat"]) / 10, 1)
    num("cpConHorasGB", con[con["instancia"] == "bat_G1"]["makespan"].iloc[0] / 10, 1)
    num("cpPistaMedia", np.mean([100 * (a - r.loc[i, "mvc"]) / r.loc[i, "mvc"] for i, a in zip(z["instancia"], z["makespan_pista"])]), 1)
    num("cpPistaSeg", z["segundos_pista"].max(), 1)
    num("cpPistaSegMin", z["segundos_pista"].min(), 2)
    cab = ("Instancia & \\shortstack[r]{Pista\\\\(AG, h)} & \\shortstack[r]{CP-SAT sin\\\\pista (h)} & \\shortstack[r]{CP-SAT con\\\\pista (h)} & \\shortstack[r]{Brecha sin\\\\pista (\\%)} & "
           "\\shortstack[r]{Brecha con\\\\pista (\\%)} & \\shortstack[r]{Cota de\\\\CP-SAT (h)} & \\shortstack[r]{Cota por\\\\capacidad (h)}")
    return tabular(r"@{}l r r r r r r r@{}", cab, filas)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    generar()
