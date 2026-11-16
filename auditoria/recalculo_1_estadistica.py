"""Auditoría (16-nov-2026): recalcula desde los CSV, con código propio (sin analisis_jsp ni jsp_ag), las cifras del manuscrito que salen de B1 a B8, y las compara con
las macros de manuscrito/numeros.tex. Imprime una línea por cifra: OK si coincide (tolerancia de redondeo) o DIFIERE."""
import itertools
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RAIZ = Path(__file__).resolve().parents[1]
R = RAIZ / "experimentos" / "resultados"
NUM = {}
for m in re.finditer(r"\\newcommand\{\\(\w+)\}\{(.*)\}$", (RAIZ / "manuscrito" / "numeros.tex").read_text(encoding="utf-8"), re.M):
    NUM[m.group(1)] = re.sub(r"\\ensuremath\{(.*)\}", r"\1", m.group(2))
MALAS = []
COMPARADAS = set()
L = str.maketrans("0123456789", "ABCDEFGHIJ")


def macro(n):
    return NUM["n" + "".join(c for c in n if c.isalnum()).translate(L)]


def cmp(nombre, valor, d=1):
    COMPARADAS.add("".join(c for c in nombre if c.isalnum()).translate(L))
    esp = macro(nombre)
    if isinstance(valor, str):
        ok = esp == valor
        print(f"{'OK    ' if ok else 'DIFIERE'} {nombre:28s} texto={esp} recalculado={valor}")
    else:
        ok = abs(float(esp) - valor) <= 0.5 * 10 ** (-d) + 1e-9
        print(f"{'OK    ' if ok else 'DIFIERE'} {nombre:28s} texto={esp:>10s} recalculado={valor:.{d}f}")
    if not ok:
        MALAS.append(nombre)


def holm(p):
    p = np.asarray(p, float); o = np.argsort(p); n = len(p); adj = np.empty(n); run = 0.0
    for k, i in enumerate(o):
        run = max(run, (n - k) * p[i]); adj[i] = min(1.0, run)
    return adj


def wil(a, b):
    return 1.0 if np.all(a.values == b.values) else float(stats.wilcoxon(a.values, b.values, zero_method="wilcox").pvalue)


def exp_fmt(p):
    m, e = f"{p:.1e}".split("e")
    return f"{m}\\times10^{{{int(e)}}}"


# --- estructura de los archivos ---------------------------------------------------------------------------------------------------------------------
esperado = {"B1_base.csv": 3000, "B2b_ajustado.csv": 2250, "B2d_ajustado.csv": 1500, "B3_operadores.csv": 9000,
            "B6_supuestos.csv": 1800, "B8_bits.csv": 4500, "B4_presupuesto.csv": 400, "B2a_rejilla.csv": 7500, "B2d_rejilla.csv": 5000}
print("== filas, duplicados y semillas")
D = {}
for a, n in esperado.items():
    d = pd.read_csv(R / a)
    D[a] = d
    clave = ["instancia", "metodo", "cruza", "gray", "bits", "pop", "escala", "semilla"]
    dup = d.duplicated(clave).sum()
    print(f"{'OK' if len(d) == n and dup == 0 else 'MAL'} {a}: {len(d)} filas (esperadas {n}), {dup} duplicados, semillas {d.semilla.min()}–{d.semilla.max()}, evaluaciones {d.evaluaciones.min()}–{d.evaluaciones.max()}")

# --- referencias ---------------------------------------------------------------------------------------------------------------------------------
B7 = pd.read_csv(R / "B7_exacto.csv")
base_files = ["B1_base.csv", "B2b_ajustado.csv", "B2d_ajustado.csv", "B3_operadores.csv", "B4_presupuesto.csv", "B8_bits.csv"]
todas = pd.concat([D[a][["instancia", "mejor"]] for a in base_files])
todas = todas[~todas.instancia.str.contains("#")]
mvc = todas.groupby("instancia")["mejor"].min()
for i, g in B7.groupby("instancia"):
    mvc[i] = min(mvc[i], g["makespan"].min())
ev = [f"bat_G{g}" for g in range(1, 6)] + [f"bat_G{g}v{k}" for g in range(1, 6) for k in range(1, 5)]
assert set(ev) == set(mvc.index), set(ev) ^ set(mvc.index)
print("== ninguna corrida bajo la cota por capacidad ni bajo la de CP-SAT")
cap = B7.groupby("instancia")["cota_capacidad"].first()
cps = B7.groupby("instancia")["cota_cpsat"].max()
for a in base_files:
    d = D[a]
    d = d[d.instancia.isin(cap.index)]
    bajo = (d["mejor"] < d["instancia"].map(np.maximum(cap, cps))).sum()
    print(f"{'OK' if bajo == 0 else 'MAL'} {a}: {bajo} corridas bajo la mejor cota")


def gap(d):
    d = d.copy()
    d["gap"] = 100 * (d["mejor"] - d["instancia"].map(mvc)) / d["instancia"].map(mvc)
    return d


def med(d, por):
    return gap(d).groupby(["instancia"] + por)["gap"].median().unstack(por)


print("== B1")
M = med(D["B1_base.csv"], ["metodo"])
reglas = pd.read_csv(R / "B5_reglas.csv")
mop = reglas[(reglas.modo == 0) & (reglas.regla == "MOPNR")].set_index("instancia")["makespan"]
mopg = 100 * (mop - mvc.reindex(mop.index)) / mvc.reindex(mop.index)
for m, n in (("binaria", "gapBinaria"), ("permutacion", "gapPermutacion"), ("llaves", "gapLlaves"), ("aleatoria", "gapAleatoria")):
    cmp(n, float(M[m].mean()))
cmp("gapMOPNR", float(mopg.mean()))
fr = stats.friedmanchisquare(*[M[c] for c in ("binaria", "permutacion", "llaves", "aleatoria")])
cmp("friedmanChi", float(fr.statistic))
pares = [("permutacion", "llaves"), ("permutacion", "binaria"), ("llaves", "binaria")]
ph = holm([wil(M[a], M[b]) for a, b in pares] + [wil(M["llaves"], M["aleatoria"]), wil(M["binaria"], M["aleatoria"])])
for (a, b), q in zip(pares, ph):
    cmp(f"holm{a[:4]}{b[:4]}", exp_fmt(q))
    cmp(f"gana{a[:4]}{b[:4]}", str(int((M[a] < M[b]).sum())))
mwp = [stats.mannwhitneyu(D["B1_base.csv"].query("instancia==@i and metodo=='permutacion'")["mejor"], D["B1_base.csv"].query("instancia==@i and metodo=='llaves'")["mejor"], alternative="two-sided").pvalue for i in ev]
cmp("mwSignif", str(int((holm(mwp) < 0.05).sum())))
a12 = []
for i in ev:
    u = D["B1_base.csv"].query("instancia==@i and metodo=='permutacion'")["mejor"].values
    v = D["B1_base.csv"].query("instancia==@i and metodo=='llaves'")["mejor"].values
    a12.append(((u[:, None] < v[None, :]).mean() + 0.5 * (u[:, None] == v[None, :]).mean()))
cmp("aBCPerm", float(np.mean(a12)), 2)
med1 = D["B1_base.csv"].groupby(["instancia", "metodo"])["mejor"].median().unstack()
ah = (mop - med1["permutacion"]) / 10
cmp("ahorroMin", float(ah.min())); cmp("ahorroMax", float(ah.max())); cmp("ahorroPct", float((100 * (mop - med1["permutacion"]) / mop).mean()))
orig = [f"bat_G{g}" for g in range(1, 6)]
bnd = np.maximum(cap, cps)
gb = 100 * (mvc[orig] - bnd[orig]) / bnd[orig]
cmp("cotaMvcMin", float(gb.min())); cmp("cotaMvcMax", float(gb.max()))

print("== B2")
cfg = json.loads((R / "B2_mejor_config.json").read_text(encoding="utf-8"))
aj = D["B2b_ajustado.csv"]
A = med(aj, ["metodo"])
for m in ("binaria", "permutacion", "llaves"):
    cmp(f"ajustada{m[:4].capitalize()}", float(A[m].mean()))
    cmp(f"mejoraAj{m[:4].capitalize()}", str(int((A[m] < M[m]).sum())))
    cmp(f"ajMenorMOPNR{m[:4].capitalize()}", str(int((A[m] < mopg.reindex(A.index)).sum())))
fr = stats.friedmanchisquare(*[A[c] for c in ("binaria", "permutacion", "llaves")])
cmp("friedmanAjP", "p=" + exp_fmt(fr.pvalue))
ph = holm([wil(A[a], A[b]) for a, b in pares])
for (a, b), q in zip(pares, ph):
    cmp(f"holmAj{a[:4]}{b[:4]}", exp_fmt(q)); cmp(f"ganaAj{a[:4]}{b[:4]}", str(int((A[a] < A[b]).sum())))
g = D["B2a_rejilla.csv"]
m = g.groupby(["metodo", "instancia", "escala", "pop"])["mejor"].mean().reset_index()
m["rel"] = m["mejor"] / m.groupby(["metodo", "instancia"])["mejor"].transform("min")
s = m.groupby(["metodo", "escala", "pop"])["rel"].mean().reset_index()
for met in ("binaria", "permutacion", "llaves"):
    t = s[s.metodo == met].sort_values("rel").iloc[0]
    ok = (t.escala, t["pop"]) == (cfg[met]["escala"], cfg[met]["pop"])
    print(f"{'OK    ' if ok else 'DIFIERE'} mejor celda de {met}: recalculada escala {t.escala:g} pob {int(t['pop'])}; archivo {cfg[met]['escala']:g}/{cfg[met]['pop']}")
    base = s[(s.metodo == met) & (s.escala == 1.0) & (s["pop"] == 100)].iloc[0]["rel"]
    print(f"        exceso base {100 * (base - 1):.2f} %, mejor {100 * (t.rel - 1):.2f} %, peor {100 * (s[s.metodo == met].rel.max() - 1):.1f} %")
# ¿queda la mejor celda en el borde?
for met in ("binaria", "permutacion", "llaves"):
    t = s[s.metodo == met].sort_values("rel").iloc[0]
    print(f"        {met}: escalas probadas {sorted(s[s.metodo == met].escala.unique())[0]:g}–{sorted(s[s.metodo == met].escala.unique())[-1]:g}, poblaciones {int(s[s.metodo == met]['pop'].min())}–{int(s[s.metodo == met]['pop'].max())}; mejor en el borde: "
          f"{t.escala in (s[s.metodo == met].escala.min(), s[s.metodo == met].escala.max()) or t['pop'] in (s[s.metodo == met]['pop'].min(), s[s.metodo == met]['pop'].max())}")

print("== B2d (ajuste propio de cada cruza)")
b2b = aj.copy(); b2b["cruza"] = b2b["metodo"].map({"binaria": "dos_puntos", "permutacion": "pox", "llaves": "uniforme"})
P = med(pd.concat([b2b, D["B2d_ajustado.csv"]]), ["metodo", "cruza"])
for (a, b), n in ((("binaria", "dos_puntos"), "propiaBinadospuntos"), (("binaria", "uniforme"), "propiaBinauniforme"), (("llaves", "uniforme"), "propiaLlavuniforme"),
                  (("llaves", "dos_puntos"), "propiaLlavdospuntos"), (("permutacion", "pox"), "propiaPermpox")):
    cmp(n, float(P[(a, b)].mean()))
cmp("propiaDifBiLl", abs(float(P[("binaria", "uniforme")].mean() - P[("llaves", "uniforme")].mean())))
x, y = P[("llaves", "uniforme")], P[("binaria", "uniforme")]
cmp("propiaLlBiGana", str(int((x < y).sum())))
q = holm([wil(x, y), wil(P[("permutacion", "pox")], x)])
print(f"        Holm llaves-unif vs binaria-unif = {q[0]:.4f}; permutación vs llaves-unif = {exp_fmt(q[1])}")

print("== B3 (ablación)")
b3 = D["B3_operadores.csv"].copy(); b3["cruza"] = b3["cruza"].fillna(""); b3["gray"] = b3["gray"].astype(str).str.lower().isin(["true", "1"])
b3["v"] = list(zip(b3.metodo, b3.cruza, b3.gray))
O = med(b3, ["v"])
mm = O.mean()
for k, v in mm.items():
    print(f"        {k}: {v:.2f}")
fr = stats.friedmanchisquare(*[O[c] for c in O.columns])
cmp("friedmanOpChi", float(fr.statistic))
print("== B8 (bits)")
b8 = D["B8_bits.csv"]
b3n = b3[(b3.metodo == "binaria") & (~b3.gray)].assign(bits=8)
dd = pd.concat([b8, b3n])
for bits in (4, 8, 12, 16):
    for c in ("dos_puntos", "uniforme"):
        z = dd[(dd.cruza == c) & (dd.bits == bits)]
        cmp(f"bits{bits}{c.replace('_', '')}", float(med(z, ["metodo"])["binaria"].mean()))

print("== B4 (presupuesto)")
z = np.load(R / "B4_curvas.npz")
elite_b4 = D["B4_presupuesto.csv"].groupby("metodo")["elite"].first().to_dict()      # la élite de cada método decide cuántas evaluaciones hay por generación
filas = {}
for k in z.keys():
    p = k.split("|"); filas.setdefault((p[1], p[2]), []).append(z[k].astype(float))
for e in (10000, 30000, 100000, 300000):
    Mx = pd.DataFrame({m: [100 * (np.median(np.array(filas[(inst, m)])[:, min(int((e - 100) // (100 - elite_b4[m])), len(filas[(inst, m)][0]) - 1)]) - mvc[inst]) / mvc[inst] for inst in orig]
                       for m in ("binaria", "permutacion", "llaves", "aleatoria")}, index=orig)
    for m in ("binaria", "permutacion", "llaves", "aleatoria"):
        cmp(f"pres{e}{m[:4].capitalize()}", float(Mx[m].mean()))
cmp("presMOPNR", float(mopg[orig].mean()))
# la última lectura de la curva debe coincidir con el CSV de la corrida larga
b4 = D["B4_presupuesto.csv"]
ult = {k: np.array(v)[:, -1] for k, v in filas.items()}
dif = sum(int(sorted(ult[(i, m)]) != sorted(b4[(b4.instancia == i) & (b4.metodo == m)]["mejor"])) for (i, m) in ult)
print(f"{'OK' if dif == 0 else 'MAL'} el último punto de cada curva coincide con el CSV de B4 ({dif} diferencias)")

print("== B6 (supuestos)")
b6 = D["B6_supuestos.csv"].copy(); b6["modo"] = b6.instancia.str.split("#").str[1].astype(int); b6["inst"] = b6.instancia.str.split("#").str[0]
b1o = D["B1_base.csv"][D["B1_base.csv"].instancia.isin(orig)].copy(); b1o["modo"] = 0; b1o["inst"] = b1o.instancia
b6 = pd.concat([b6, b1o])
for modo in range(4):
    zz = b6[b6.modo == modo]
    mv = zz.groupby("inst")["mejor"].min()
    rm = reglas[(reglas.modo == modo) & (reglas.regla == "MOPNR")].set_index("instancia")["makespan"]
    mv = np.minimum(mv, rm.reindex(mv.index))
    zz = zz.assign(gap=100 * (zz["mejor"] - zz["inst"].map(mv)) / zz["inst"].map(mv))
    Mx = zz.groupby(["inst", "metodo"])["gap"].median().unstack()
    letra = "ABCD"[modo]
    cmp(f"modoMvc{letra}".replace("A", "A"), float(mv.mean() / 10))
    for m in ("binaria", "permutacion", "llaves", "aleatoria"):
        cmp(f"modo{letra}{m[:4].capitalize()}".replace("modoA", "modoA"), float(Mx[m].mean()))
print("== B7")
for g in range(1, 6):
    i = f"bat_G{g}"
    s_, c_ = B7[(B7.instancia == i) & (B7.variante == "sin_pista")].iloc[0], B7[(B7.instancia == i) & (B7.variante == "con_pista")].iloc[0]
    cmp(f"cpSinG{g}", float(100 * (s_.makespan - mvc[i]) / mvc[i])); cmp(f"cpConG{g}", float(100 * (c_.makespan - mvc[i]) / mvc[i])); cmp(f"cpPistaG{g}", float(100 * (s_.makespan_pista - mvc[i]) / mvc[i]))

print("== resto de las macros usadas en el texto")
# MOPNR y brechas base por grupo
tam = pd.Series({i: i[4:6] for i in ev})
mg = mopg.groupby(tam.reindex(mopg.index)).mean()
for g in ("G1", "G2", "G3", "G4", "G5"):
    cmp(f"mopnr{g}", float(mg[g]))
    for m in ("binaria", "permutacion", "llaves"):
        cmp(f"base{g}{m[:4].capitalize()}", float(M[m].groupby(tam.reindex(M.index)).mean()[g]))
# ahorro por grupo en horas (medianas)
for g in range(1, 6):
    cmp(f"ahorroG{g}", float(ah[f"bat_G{g}"]))
# P de Holm de las comparaciones planeadas de la ablación (12 pares, mismo orden que el texto)
pl = [(("binaria", "dos_puntos", False), ("binaria", "uniforme", False)), (("binaria", "dos_puntos", False), ("binaria", "un_punto", False)),
      (("binaria", "dos_puntos", False), ("binaria", "dos_puntos", True)), (("permutacion", "pox", False), ("permutacion", "ox", False)),
      (("permutacion", "pox", False), ("permutacion", "ppx", False)), (("permutacion", "ox", False), ("permutacion", "ppx", False)),
      (("llaves", "uniforme", False), ("llaves", "dos_puntos", False)), (("llaves", "uniforme", False), ("llaves", "aritmetica", False)),
      (("llaves", "dos_puntos", False), ("llaves", "aritmetica", False)), (("permutacion", "pox", False), ("llaves", "uniforme", False)),
      (("llaves", "uniforme", False), ("binaria", "uniforme", False)), (("binaria", "uniforme", False), ("binaria", "dos_puntos", False))]
ph = holm([wil(O[a], O[b]) for a, b in pl])
for (a, b), q, tag in zip(pl, ph, ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "BA", "BB"]):
    s = f"{q:.2g}"
    cmp(f"opHolm{tag}", s)
    cmp(f"opGana{tag}", str(int((O[a] < O[b]).sum())))
# PPX (la peor de la permutación) y OX frente a la mejor de llaves y de binaria, más llaves contra binaria (Holm sobre 5 pares, como en el texto)
ppx, ox, ll_, bi_ = ("permutacion", "ppx", False), ("permutacion", "ox", False), ("llaves", "uniforme", False), ("binaria", "uniforme", False)
pw = [(ppx, ll_), (ppx, bi_), (ll_, bi_), (ox, ll_), (ox, bi_)]
q = holm([wil(O[a], O[b]) for a, b in pw])
fp = lambda v: f"{v:.2f}" if v >= 0.01 else exp_fmt(v)
for (a, b), qq, tag in zip(pw, q, ["pPeorLl", "pPeorBi", "llBi", "pOxLl", "pOxBi"]):
    cmp("op" + tag, fp(qq)); cmp("opGana" + tag, str(int((O[a] < O[b]).sum()))); cmp("opPierde" + tag, str(int((O[a] > O[b]).sum())))
# B2d: Holm (no crudo)
x, y = P[("llaves", "uniforme")], P[("binaria", "uniforme")]
q = holm([wil(x, y), wil(P[("permutacion", "pox")], x)])
cmp("propiaLlBiP", fp(q[0])); cmp("propiaPeLlP", exp_fmt(q[1]))
# B2: exceso de la rejilla
for met in ("binaria", "permutacion", "llaves"):
    tt = s_ = None
for met in ("binaria", "permutacion", "llaves"):
    sm = D["B2a_rejilla.csv"].groupby(["metodo", "instancia", "escala", "pop"])["mejor"].mean().reset_index()
    sm["rel"] = sm["mejor"] / sm.groupby(["metodo", "instancia"])["mejor"].transform("min")
    ss = sm.groupby(["metodo", "escala", "pop"])["rel"].mean().reset_index()
    ss = ss[ss.metodo == met]
    cmp(f"excesoBase{met[:4].capitalize()}", float(100 * (ss[(ss.escala == 1.0) & (ss["pop"] == 100)].rel.iloc[0] - 1)))
    cmp(f"excesoMejor{met[:4].capitalize()}", float(100 * (ss.rel.min() - 1)), 2)
    cmp(f"excesoPeor{met[:4].capitalize()}", float(100 * (ss.rel.max() - 1)))
# tiempos de B7 (máquina sin otra carga)
sp = B7[B7.variante == "sin_pista"]
cmp("cpPistaSeg", float(sp.segundos_pista.max())); cmp("cpPistaSegMin", float(sp.segundos_pista.min()), 2)
# CP-SAT: medias
for v, tag in (("sin_pista", "Sin"), ("con_pista", "Con")):
    z_ = B7[B7.variante == v]
    cmp(f"cp{tag}Media", float(np.mean([100 * (a_ - mvc[i_]) / mvc[i_] for i_, a_ in zip(z_.instancia, z_.makespan)])))
z_ = B7[B7.variante == "sin_pista"]
cmp("cpPistaMedia", float(np.mean([100 * (a_ - mvc[i_]) / mvc[i_] for i_, a_ in zip(z_.instancia, z_.makespan_pista)])))
cmp("cpMejoraN", str(int(sum(B7[(B7.instancia == i_) & (B7.variante == "con_pista")].makespan.iloc[0] < B7[(B7.instancia == i_) & (B7.variante == "sin_pista")].makespan_pista.iloc[0] for i_ in orig))))
cmp("cpCotaMax", float(B7.cota_cpsat.max() / 10))
cmp("cpConHorasGB", float(B7[(B7.instancia == "bat_G1") & (B7.variante == "con_pista")].makespan.iloc[0] / 10))
print("== B0 (parámetros comunes): se repite la elección a partir de la confirmación")
b0a, b0b = pd.read_csv(R / "B0a_comunes.csv"), pd.read_csv(R / "B0b_confirmacion.csv")
esp0a, esp0b = 80 * 3 * 10 * 2 + 400 * 3 * 10, 3 * 6 * 10 * 10           # 80 configuraciones (binaria y permutación) y 400 (llaves) por 3 semillas y 10 instancias; 6 finalistas por método, 10 semillas
dup0 = int(b0a.duplicated(["metodo", "instancia", "semilla", "torneo", "elite", "pc", "sigma"]).sum())
print(f"{'OK' if (len(b0a), len(b0b), dup0) == (esp0a, esp0b, 0) else 'MAL'} B0a: {len(b0a)} corridas (esperadas {esp0a}), {dup0} duplicados; B0b: {len(b0b)} (esperadas {esp0b})")
claves = ["torneo", "elite", "pc", "sigma"]
mm_ = b0b.groupby(["metodo", *claves, "instancia"])["mejor"].mean().reset_index()
mm_["rel"] = mm_["mejor"] / mm_.groupby(["metodo", "instancia"])["mejor"].transform("min")
sc = mm_.groupby(["metodo", *claves])["rel"].mean().reset_index()
for met, tag in (("binaria", "Bina"), ("permutacion", "Perm"), ("llaves", "Llav")):
    t = sc[sc.metodo == met].sort_values("rel")
    b = t.iloc[0]
    par = t[(t.torneo == 3) & (t.elite == 2) & (abs(t.pc - 0.9) < 1e-9) & (abs(t.sigma - 0.15) < 1e-9)].iloc[0]
    cmp(f"bcTorneo{tag}", str(int(b.torneo))); cmp(f"bcElite{tag}", str(int(b.elite))); cmp(f"bcCruza{tag}", f"{b.pc:g}")
    if met == "llaves":
        cmp("bcSigmaLlav", f"{b.sigma:g}")
    cmp(f"bcPartida{tag}", float(100 * (par.rel - 1))); cmp(f"bcElegido{tag}", float(100 * (b.rel - 1)))
rg_ = reglas[reglas.modo == 0].pivot(index="instancia", columns="regla", values="makespan")
for regla in ("SPT", "MWKR"):
    cmp(f"gap{regla}", float((100 * (rg_[regla] - mvc.reindex(rg_.index)) / mvc.reindex(rg_.index)).mean()))
cmp("mopnrMejorRegla", str(int((rg_["MOPNR"] <= rg_[["SPT", "MWKR"]].min(axis=1)).sum())))
print("\nCifras que difieren:", MALAS if MALAS else "ninguna")

usadas = set()
for f in list((RAIZ / "manuscrito" / "secciones").glob("*.tex")) + [RAIZ / "manuscrito" / "resumen.tex"]:
    usadas.update(re.findall(r"\\n([A-Za-z]+)", f.read_text(encoding="utf-8")))
sin = sorted(u for u in usadas if "n" + u in {"n" + k[1:] for k in ["n" + x for x in NUM]} and u in {k[1:] for k in ["n" + x for x in []]} or (u in {x for x in NUM} is False))
no_comp = sorted(u for u in usadas if u.startswith("") and ("n" + u) not in () and u in {k for k in NUM} is False)
print("Macros usadas en el texto y no comparadas con un recálculo propio:", sorted(u for u in usadas if u in {k[1:] for k in NUM} and u not in COMPARADAS))
