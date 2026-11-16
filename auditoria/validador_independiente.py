"""Validador de calendarios de G1 escrito aparte: no importa nada de experimentos/ (ni jsp_ag ni analisis_jsp). Lee las tablas transcritas
(instancias/baterias_parametros.json), arma los 10 lotes de G1 desde la lista de la tabla A.4 y revisa un calendario dado como
{"inicios": [...], "maquinas": [...]} con una operación por posición (lotes en el orden de la lista, operaciones en el orden de su ruta; `inicios` es el
inicio del proceso y `maquinas` el índice global de máquina: etapas 1 a 7 con 2, 2, 2, 3, 1, 2 y 1 máquinas). Reglas del modo base: el bloque
(preparación + proceso) de cada operación no empieza antes de que termine la operación anterior del lote ni antes de que la máquina quede libre; la preparación es la fija
de la etapa, salvo en el recocido cuando la máquina ya procesó un lote (entonces, la entrada de la matriz de cambio entre la familia del anterior y la del actual)."""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
D = json.loads((RAIZ / "experimentos" / "instancias" / "baterias_parametros.json").read_text(encoding="utf-8"))


def decimas(x: float) -> int:
    return int(round(10 * x))


def lotes_g1():
    out = []
    for lote in D["G1_trabajos"]:
        fam = lote["familia"]
        ops = []
        for etapa, _capa in D["rutas"][lote["ruta"]]["ops"]:
            e = D["etapas"][etapa - 1]
            p = D["recocido_por_familia"][fam] if e["p"] is None else e["p"]
            ops.append((etapa - 1, decimas(p), decimas(e["s"])))
        out.append({"id": lote["id"], "fam": int(fam[1]) - 1, "ops": ops})
    return out


def maquinas_por_etapa():
    ini, tot = [], 0
    for e in D["etapas"]:
        ini.append(tot)
        tot += e["maquinas"]
    return ini, tot


def validar(cal: dict) -> int:
    lotes = lotes_g1()
    ini_etapa, total = maquinas_por_etapa()
    cambio = [[decimas(x) for x in f] for f in D["cambio_recocido"]]
    pos = 0
    bloques = {m: [] for m in range(total)}
    fin_lote = []
    for lote in lotes:
        previo = 0
        for k, (etapa, p, s_fija) in enumerate(lote["ops"]):
            m, inicio = cal["maquinas"][pos], cal["inicios"][pos]
            pos += 1
            assert ini_etapa[etapa] <= m < ini_etapa[etapa] + D["etapas"][etapa]["maquinas"], f"{lote['id']} op {k + 1}: máquina {m} no es de la etapa {etapa + 1}"
            bloques[m].append((inicio, p, s_fija, lote["fam"], etapa, lote["id"], k, previo))
            previo = inicio + p                                                  # se corrige abajo con la preparación real
        fin_lote.append(previo)
    assert pos == len(cal["inicios"]) == len(cal["maquinas"]), "el calendario no tiene una entrada por operación"
    mk = 0
    for m, lista in bloques.items():
        lista.sort()
        ultimo_fin, ultima_fam = 0, None
        for inicio, p, s_fija, fam, etapa, lote_id, k, ant in lista:
            prep = cambio[ultima_fam][fam] if (etapa == 3 and ultima_fam is not None) else s_fija
            assert inicio - prep >= ultimo_fin, f"máquina {m}: el bloque de {lote_id} op {k + 1} empieza ({inicio - prep}) antes de que la máquina quede libre ({ultimo_fin})"
            ultimo_fin, ultima_fam = inicio + p, fam
            mk = max(mk, ultimo_fin)
            bloques[m][bloques[m].index((inicio, p, s_fija, fam, etapa, lote_id, k, ant))] = (inicio, p, prep, fam, etapa, lote_id, k, ant)
    # precedencia dentro de cada lote, con la preparación real de cada operación
    reales = {(b[5], b[6]): b for lista in bloques.values() for b in lista}
    for lote in lotes:
        fin = 0
        for k in range(len(lote["ops"])):
            inicio, p, prep, *_ = reales[(lote["id"], k)]
            assert inicio - prep >= fin, f"{lote['id']}: la operación {k + 1} empieza ({inicio - prep}) antes de terminar la anterior ({fin})"
            fin = inicio + p
    return mk


if __name__ == "__main__":
    import sys
    c = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    claves = [k for k in c if isinstance(c[k], dict) and "inicios" in c[k]]
    for k in claves:
        mk = validar(c[k])
        print(f"{k}: makespan recalculado {mk / 10} h, declarado {c[k]['makespan'] / 10} h", "OK" if mk == c[k]["makespan"] else "NO COINCIDE")
