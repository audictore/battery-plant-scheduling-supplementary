"""Libro de Excel con las tablas comparativas completas (resultados/tablas_comparativas.xlsx): las del artículo y, además, el detalle por instancia que en el
texto solo aparece resumido. Uso: python3 -m analisis_jsp.exportar_tablas"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from . import bat
from . import tablas_bat as T
from .bat import GRUPOS, METODOS, RES, TODOS


def hoja(wb_writer, nombre: str, df: pd.DataFrame, nota: str | None = None, decimales: int = 2):
    df = df.copy()
    inicio = 2 if nota else 0
    df.to_excel(wb_writer, sheet_name=nombre, startrow=inicio, float_format=f"%.{decimales}f")
    ws = wb_writer.sheets[nombre]
    if nota:
        ws["A1"] = nota
        ws["A1"].font = Font(italic=True)
    for c in ws[inicio + 1]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="DDDDDD")
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.column_dimensions["A"].width = 34
    for i in range(2, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(i)].width = 16
    ws.freeze_panes = ws.cell(row=inicio + 2, column=2)


def main():
    x = T.cargar()
    r = x["ref"]
    mvc = r["mvc"]
    orig = [f"bat_{g}" for g in GRUPOS]
    out = RES / "tablas_comparativas.xlsx"
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        # 1. originales
        med = x["b1"].groupby(["instancia", "metodo"])["mejor"].median().unstack() / 10
        reg = x["b5"][x["b5"]["modo"] == 0].pivot(index="instancia", columns="regla", values="makespan") / 10
        o = pd.DataFrame({"Cota inferior (h)": r.loc[orig, "cota"] / 10, "Mejor conocido (h)": mvc[orig] / 10, "MOPNR (h)": reg.loc[orig, "MOPNR"], "MWKR (h)": reg.loc[orig, "MWKR"], "SPT (h)": reg.loc[orig, "SPT"]})
        for m in TODOS:
            o[f"{bat.NOMBRE[m]}, mediana base (h)"] = med.loc[orig, m]
        o["CP-SAT sin pista (h)"] = r.loc[orig, "cpsat_sin"] / 10
        o["CP-SAT con pista (h)"] = r.loc[orig, "cpsat_con"] / 10
        hoja(w, "Originales", o, "Tiempo total en horas. Mediana de 30 corridas con parámetros base; CP-SAT con 300 s y 8 hilos.", 1)
        # 2. por instancia
        d1 = T.brechas(x["b1"], mvc)
        pi = bat.medianas(d1, ["metodo"]).add_prefix("Base: ")
        for clave, rot in (("b2b", "Ajustada: "),):
            pi = pi.join(bat.medianas(T.brechas(x[clave], mvc), ["metodo"]).add_prefix(rot))
        rr = x["b5"][x["b5"]["modo"] == 0].pivot(index="instancia", columns="regla", values="makespan")
        for regla in ("MOPNR", "MWKR", "SPT"):
            pi[f"Regla {regla}"] = 100 * (rr[regla] - mvc.reindex(rr.index)) / mvc.reindex(rr.index)
        pi.insert(0, "Mejor conocido (h)", mvc.reindex(pi.index) / 10)
        pi.insert(1, "Cota inferior (h)", r["cota"].reindex(pi.index) / 10)
        hoja(w, "Por instancia (brecha %)", pi, "Brecha (%) respecto del mejor conocido de cada instancia: mediana de 30 corridas.")
        # 3. resumen por grupo
        g = T.por_tamano(pi.drop(columns=["Mejor conocido (h)", "Cota inferior (h)"]))
        g.loc["Las 25"] = pi.drop(columns=["Mejor conocido (h)", "Cota inferior (h)"]).mean()
        hoja(w, "Resumen por grupo", g, "Media de la brecha (%) por grupo de tamaño (5 instancias por grupo).")
        # 4. ablación
        if "b3" in x:
            b3 = x["b3"].copy()
            b3["cruza"] = b3["cruza"].fillna("")
            b3["gray"] = b3["gray"].astype(str).str.lower().isin(["true", "1"])
            b3["v"] = [T.ETIQ[k] for k in zip(b3["metodo"], b3["cruza"], b3["gray"])]
            M = bat.medianas(T.brechas(b3, mvc), ["v"])
            M.loc["MEDIA"] = M.mean()
            hoja(w, "Ablación de operadores", M, "Brecha (%) mediana de 30 corridas por instancia y variante (parámetros base).")
        # 5. rejilla
        g1 = pd.read_csv(RES / "B2a_rejilla.csv")
        m = g1.groupby(["metodo", "instancia", "escala", "pop"])["mejor"].mean().reset_index()
        m["exceso_pct"] = 100 * (m["mejor"] / m.groupby(["metodo", "instancia"])["mejor"].transform("min") - 1)
        rej = m.groupby(["metodo", "escala", "pop"])["exceso_pct"].mean().unstack("pop")
        hoja(w, "Rejilla de ajuste", rej, "Exceso medio (%) sobre la mejor celda de cada instancia de ajuste, por codificación, escala de mutación (filas) y población (columnas).")
        # 6. otras tablas del artículo, como están en el texto (se leen del .tex generado)
        for nombre, fn in (("Cruzas propias", T.tabla_cruzas_propias), ("Resolución de la binaria", T.tabla_bits), ("Presupuesto", T.tabla_presupuesto), ("Supuestos de modelado", T.tabla_supuestos), ("CP-SAT", T.tabla_exacto)):
            tex = fn(x)
            if tex is None:
                continue
            filas = []
            for f in tex.split("\n"):
                if "&" not in f:
                    continue
                f = f.strip()
                if f.endswith("\\\\"):
                    f = f[:-2]                                        # fin de fila
                f = f.replace("\\shortstack[r]{", "").replace("}", "").replace("\\\\", " ").replace("\\%", "%").replace("\\,", "").replace("$", "")
                filas.append(f)
            df = pd.DataFrame([[c.strip() for c in f.split("&")] for f in filas[1:]], columns=[c.strip() for c in filas[0].split("&")])
            hoja(w, nombre, df.set_index(df.columns[0]), "Igual que en el artículo.")
        # 7. reglas por modo
        rm = x["b5"].pivot_table(index=["modo", "instancia"], columns="regla", values="makespan") / 10
        hoja(w, "Reglas por modo (h)", rm, "Tiempo total (h) de cada regla de despacho en cada modo del decodificador.", 1)
    print(out)


if __name__ == "__main__":
    main()
