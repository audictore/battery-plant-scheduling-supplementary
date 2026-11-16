"""Auditoría (16-nov-2026): compara la transcripción (instancias/baterias_parametros.json) con el documento original de Mendeley Data (Standard Test
Instances.docx, descargado el 16-nov-2026 a fuente/, SHA-256 comprobado), leyendo el .docx con código propio, y rehace con código propio el número de
operaciones de cada grupo y la cota por capacidad del recocido (la que aparece en B7_exacto.csv)."""
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DOCX = RAIZ / "fuente" / "Standard_Test_Instances.docx"
J = json.loads((RAIZ / "experimentos" / "instancias" / "baterias_parametros.json").read_text(encoding="utf-8"))
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
mal = 0


def chk(nombre, ok):
    global mal
    print(("OK   " if ok else "MAL  ") + nombre)
    mal += not ok


sha = hashlib.sha256(DOCX.read_bytes()).hexdigest()
chk(f"SHA-256 del documento = el registrado en el JSON ({sha[:12]}…)", sha == J["fuente"]["sha256"])
raiz = ET.fromstring(zipfile.ZipFile(DOCX).read("word/document.xml"))
T = []
for tbl in raiz.iter(W + "tbl"):
    T.append([[("".join(x.text or "" for x in tc.iter(W + "t"))).strip().replace("‑", "-") for tc in tr.findall(W + "tc")] for tr in tbl.iter(W + "tr")])
chk("6 tablas en el documento", len(T) == 6)
# A.1 etapas
for fila, e in zip(T[0][1:], J["etapas"]):
    chk(f"A.1 etapa {fila[0]} {fila[1]}", int(fila[0]) == e["j"] and int(fila[2]) == e["maquinas"] and float(fila[4]) == e["s"] and (e["p"] is None) == ("family" in fila[3].lower() or not fila[3][0].isdigit()) and (e["p"] is None or float(fila[3]) == e["p"]))
# A.2 familias y rutas
fam_t = {}
rutas = {}
for fila in T[1][1:]:
    if fila[0].startswith("F") and fila[1]:
        fam_t[fila[0]] = float(fila[1])
    pid = fila[2]
    pares = [tuple(int(x) for x in p.strip("()").split(",")) for p in fila[3].replace("),(", ")|(").split("|")]
    rutas[pid] = (fila[0] if fila[0].startswith("F") else None, pares, int(fila[4]))
fam_actual = None
for pid, (f, pares, tot) in rutas.items():
    pass
# las filas sin familia heredan la de la fila anterior
fam_actual = None
for fila in T[1][1:]:
    if fila[0].startswith("F"):
        fam_actual = fila[0]
    pid = fila[2]
    pares = [tuple(int(x) for x in p.strip("()").split(",")) for p in fila[3].replace("),(", ")|(").split("|")]
    chk(f"A.2 {pid}: familia {fam_actual}, {len(pares)} operaciones (columna «Total ops» = {fila[4]})", J["rutas"][pid]["familia"] == fam_actual and [tuple(x) for x in J["rutas"][pid]["ops"]] == pares and len(pares) == int(fila[4]))
chk("A.2 tiempos de recocido por familia", fam_t == J["recocido_por_familia"])
# A.3 matriz
mat = [[float(x) for x in f[1:]] for f in T[2][1:]]
chk("A.3 matriz de cambio 4x4", mat == J["cambio_recocido"])
# A.4 G1
for fila, l in zip(T[3][1:], J["G1_trabajos"]):
    ok = fila[0] == l["id"] and fila[1] == l["familia"] and fila[2] == l["ruta"] and int(fila[3]) == l["entrega"]
    tiempos = [float(x.split(":")[1]) for x in fila[4].split(",") if ":" in x]
    pares = [tuple(int(y) for y in x.split(":")[0].strip().strip("()").split(",")) for x in fila[4].split("), (")] if False else None
    chk(f"A.4 {l['id']}: familia, ruta y fecha; suma de procesos {sum(tiempos):.1f} h (columna acumulada: {fila[5]})", ok and abs(sum(tiempos) - float(fila[5])) < 1e-6)
# A.5 grupos
for fila in T[4][1:]:
    g = fila[0]
    gj = J["grupos"][g]
    chk(f"A.5 {g}: {fila[1]} lotes y composición {fila[3:7]}", gj["trabajos"] == int(fila[1]) and gj["familias"] == [int(x) for x in fila[3:7]] and gj["ops_estimadas"] == int(fila[8]))
# A.6 conteos por ruta
for fila in T[5][1:]:
    pid = fila[0]
    if pid.lower().startswith("total"):
        chk(f"A.6 fila de totales {fila[2:6]} = lotes de G2 a G5", [int(x) for x in fila[2:6]] == [J["grupos"][g]["trabajos"] for g in ("G2", "G3", "G4", "G5")])
        continue
    for g, v in zip(("G2", "G3", "G4", "G5"), fila[2:6]):
        if J["conteo_rutas"][g].get(pid, 0) != int(v):
            chk(f"A.6 {pid} {g}", False)
chk("A.6 conteos por ruta de G2 a G5", True)
for g in ("G2", "G3", "G4", "G5"):
    gj = J["grupos"][g]
    porfam = [0] * 4
    for pid, n in J["conteo_rutas"][g].items():
        porfam[int(J["rutas"][pid]["familia"][1]) - 1] += n
    chk(f"{g}: los conteos por ruta suman {sum(J['conteo_rutas'][g].values())} lotes y reproducen la composición por familia", sum(J["conteo_rutas"][g].values()) == gj["trabajos"] and porfam == gj["familias"])

# operaciones por grupo, desde las rutas del documento
largo = {pid: len(r[1]) for pid, r in rutas.items()}
ops = {"G1": sum(largo[l["ruta"]] for l in J["G1_trabajos"])}
for g in ("G2", "G3", "G4", "G5"):
    ops[g] = sum(largo[pid] * n for pid, n in J["conteo_rutas"][g].items())
print("operaciones por grupo recalculadas:", ops)
chk("93, 189, 280, 376 y 467 operaciones (el documento estima 85, 172, 258, 344 y 430)", list(ops.values()) == [93, 189, 280, 376, 467])

# cota por capacidad del recocido, independiente (décimas de hora)
D = lambda x: int(round(10 * x))
cota = {}
cambio = [[D(x) for x in f] for f in J["cambio_recocido"]]
min_cambio = min(min(f) for f in cambio)
fija_rec = D(J["etapas"][3]["s"])
st = J["etapas"]


def tiempo(etapa, fam):  # etapa 0-based
    e = st[etapa]
    return D(J["recocido_por_familia"][fam]) if e["p"] is None else D(e["p"])


def rutas_de(g):
    if g == "G1":
        return [J["rutas"][l["ruta"]] for l in J["G1_trabajos"]]
    out = []
    for pid, n in J["conteo_rutas"][g].items():
        out += [J["rutas"][pid]] * n
    return out


for g in ops:
    carga, cabezas, colas = 0, [], []
    for r in rutas_de(g):
        fam = r["familia"]
        etapas = [o[0] - 1 for o in r["ops"]]
        carga += sum(tiempo(e, fam) + min(min_cambio, fija_rec) for e in etapas if e == 3)
        primero = etapas.index(3)
        ultimo = max(i for i, e in enumerate(etapas) if e == 3)
        cabezas.append(sum(tiempo(e, fam) + D(st[e]["s"]) for e in etapas[:primero]))
        colas.append(sum(tiempo(e, fam) + D(st[e]["s"]) for e in etapas[ultimo + 1:]))
    cota[g] = min(cabezas) + -(-carga // 3) + min(colas)
b7 = pd.read_csv(RAIZ / "experimentos" / "resultados" / "B7_exacto.csv").groupby("instancia")["cota_capacidad"].first()
for g, v in cota.items():
    chk(f"cota por capacidad de {g}: recalculada {v / 10:.1f} h, en B7_exacto.csv {b7['bat_' + g] / 10:.1f} h", v == b7["bat_" + g])
print("\nTranscripción:", "sin discrepancias" if not mal else f"{mal} discrepancias")
