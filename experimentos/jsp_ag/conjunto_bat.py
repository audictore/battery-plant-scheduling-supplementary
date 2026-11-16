"""Conjuntos de instancias del estudio de la planta de baterías. Las cinco originales (G1 a G5) y, de cada una, variantes con los mismos lotes por
familia y la ruta de cada lote elegida al azar entre las de su familia (hfs.variante): 4 de evaluación (v1 a v4) y 2 de ajuste (t1 y t2)."""
GRUPOS = ("G1", "G2", "G3", "G4", "G5")
ORIGINALES = [f"bat_{g}" for g in GRUPOS]
EVALUACION = ORIGINALES + [f"bat_{g}v{k}" for g in GRUPOS for k in range(1, 5)]       # 25 instancias
AJUSTE = [f"bat_{g}t{k}" for g in GRUPOS for k in (1, 2)]                            # 10 instancias, distintas de las anteriores
METODOS = ("binaria", "permutacion", "llaves")
