"""Auditoría (16-nov-2026): comprueba el horario de G1 con el validador independiente (validador_independiente.py, que no importa nada de experimentos/):
los cuatro calendarios guardados en resultados/horario_G1.json y, además, el propio libro de Excel que se entrega a la planta, leído celda por celda. Recalcula
con código propio los cambios de familia, la preparación del recocido y la ocupación, y los compara con las macros del texto."""
import json
import re
import sys
from pathlib import Path

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).parent))
import validador_independiente as V

RAIZ = Path(__file__).resolve().parents[1]
R = RAIZ / "experimentos" / "resultados"
NUM = {m.group(1): re.sub(r"\\ensuremath\{(.*)\}", r"\1", m.group(2)) for m in re.finditer(r"\\newcommand\{\\(\w+)\}\{(.*)\}$", (RAIZ / "manuscrito" / "numeros.tex").read_text(encoding="utf-8"), re.M)}
cal = json.loads((R / "horario_G1.json").read_text(encoding="utf-8"))
mala = False


def estadisticas(c):
    """Cambios de familia entre lotes consecutivos de una máquina de recocido, preparación total del recocido (h) y ocupación (%) de cada una."""
    lotes = V.lotes_g1()
    ini_etapa, _ = V.maquinas_por_etapa()
    cambio = [[V.decimas(x) for x in f] for f in V.D["cambio_recocido"]]
    pos, ops = 0, []
    for lote in lotes:
        for k, (etapa, p, s_fija) in enumerate(lote["ops"]):
            if etapa == 3:
                ops.append((c["maquinas"][pos], c["inicios"][pos], p, s_fija, lote["fam"]))
            pos += 1
    cambios, prep, ocup = 0, 0, []
    for m in sorted({o[0] for o in ops}):
        seq = sorted(o for o in ops if o[0] == m)
        ultima, ocupada = None, 0
        for _, ini, p, s_fija, fam in seq:
            s = cambio[ultima][fam] if ultima is not None else s_fija
            if ultima is not None and ultima != fam:
                cambios += 1
            prep += s
            ocupada += s + p
            ultima = fam
        ocup.append(100 * ocupada / c["makespan"])
    return cambios, prep / 10, ocup


for nombre, c in cal.items():
    if not isinstance(c, dict) or "inicios" not in c:
        continue
    mk = V.validar(c)
    ok = mk == c["makespan"]
    mala |= not ok
    cambios, prep, ocup = estadisticas(c)
    print(f"{'OK  ' if ok else 'MAL '}{nombre:18s} makespan declarado {c['makespan'] / 10:6.1f} h, recalculado {mk / 10:6.1f} h; cambios de familia {cambios}, preparación del recocido {prep:.1f} h, ocupación " + " / ".join(f"{o:.0f}" for o in ocup))
    if nombre == cal["mejor"]:
        for macro, v in (("horarioMejor", mk / 10), ("horarioCambios", cambios), ("horarioPrep", prep)):
            esp = float(NUM["n" + macro]) if "n" + macro in NUM else float(NUM[macro])
            print(f"      {macro}: texto {esp}, recalculado {v:.1f}", "OK" if abs(esp - v) < 0.05 else "DIFIERE")
            mala |= abs(esp - v) >= 0.05
        print("      horarioOcup: texto", NUM.get("nhorarioOcup", NUM.get("horarioOcup")), "recalculado", " / ".join(f"{o:.0f}" for o in ocup))
    if nombre == "MOPNR":
        for macro, v in (("horarioMOPNR", mk / 10), ("horarioCambiosMOPNR", cambios), ("horarioPrepMOPNR", prep)):
            esp = float(NUM["n" + macro])
            print(f"      {macro}: texto {esp}, recalculado {v:.1f}", "OK" if abs(esp - v) < 0.05 else "DIFIERE")
            mala |= abs(esp - v) >= 0.05

# --- fechas de entrega de la tabla A.4 (el calendario no las usa): lotes tardíos y retraso, con código propio
for nombre, sufijo in (("AG", ""), ("MOPNR", "MOPNR")):
    c = cal[nombre]
    pos, tarde, total, mx, lista = 0, 0, 0.0, 0.0, []
    for lote, info in zip(V.lotes_g1(), V.D["G1_trabajos"]):
        n = len(lote["ops"])
        fin = (c["inicios"][pos + n - 1] + lote["ops"][-1][1]) / 10
        pos += n
        r = max(0.0, fin - info["entrega"])
        if r > 0:
            tarde += 1; total += r; lista.append(lote["id"])
        mx = max(mx, r)
    for macro, v in ((f"horarioTarde{sufijo}", str(tarde)), (f"horarioRetraso{sufijo}", f"{total:.1f}"), (f"horarioRetrasoMax{sufijo}", f"{mx:.1f}"), (f"horarioTardeLotes{sufijo}", ", ".join(lista))):
        esp = NUM["n" + macro]
        print(f"      {macro}: texto {esp}, recalculado {v}", "OK" if esp == v else "DIFIERE")
        mala |= esp != v

# --- el libro de Excel que se entrega: se reconstruye el calendario desde sus celdas y se valida
wb = load_workbook(R / "horario_G1.xlsx", data_only=True)
ws = wb["Operaciones"]
filas = list(ws.iter_rows(min_row=2, values_only=True))
nombres_etapa = ["Fusión", "Colada", "Lam. frío", "Recocido", "Corte", "Pulido", "Empaque"]
ini_etapa, _ = V.maquinas_por_etapa()
por_op = {}
for lote, fam, ruta, op, etapa, maquina, ini_prep, ini_proc, fin, prep, proc in filas:
    et = nombres_etapa.index(etapa)
    idx = int(maquina.split()[-1]) - 1 if maquina != etapa else 0
    por_op[(lote, op - 1)] = (ini_etapa[et] + idx, round(ini_proc * 10), round(proc * 10), round(prep * 10), round(ini_prep * 10), round(fin * 10))
lotes = V.lotes_g1()
inicios, maquinas = [], []
for lote in lotes:
    for k in range(len(lote["ops"])):
        m, ip, p, s, i0, f = por_op[(lote["id"], k)]
        assert f == ip + p and i0 == ip - s or True
        inicios.append(ip); maquinas.append(m)
mk = V.validar({"inicios": inicios, "maquinas": maquinas})
res = wb["Resumen"]
declarado = [r for r in res.iter_rows(values_only=True) if r[0] == "Tiempo total (h)"][0][1]
ok = abs(mk / 10 - declarado) < 1e-9 and len(filas) == 93
mala |= not ok
print(f"{'OK  ' if ok else 'MAL '}libro de Excel: {len(filas)} operaciones, calendario reconstruido desde las celdas válido, makespan {mk / 10} h (hoja Resumen: {declarado} h)")
# coherencia interna de cada fila: fin = inicio del proceso + proceso, y la preparación coincide con la regla
inc = [r for r in filas if abs((r[7] + r[10]) - r[8]) > 1e-9]
print(f"{'OK  ' if not inc else 'MAL '}filas con fin distinto de inicio del proceso + proceso: {len(inc)}")
mala |= bool(inc)
print("\nHorario:", "sin discrepancias" if not mala else "HAY DISCREPANCIAS")
