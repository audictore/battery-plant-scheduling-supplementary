"""Clase base de instancia de taller de rutas variables, que usa el núcleo del algoritmo genético: una lista de órdenes y, para cada una, una lista
de pares (máquina, tiempo) en el orden de su ruta. Las instancias de la planta (con familias y cambios de preparación) están en hfs.py."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Instancia:
    nombre: str
    ordenes: tuple          # tuple de tuple de (máquina:int, tiempo:int)
    n_maquinas: int

    @property
    def n_ordenes(self) -> int:
        return len(self.ordenes)

    @property
    def n_operaciones(self) -> int:
        return sum(len(r) for r in self.ordenes)

    def carga_por_maquina(self) -> list:
        c = [0] * self.n_maquinas
        for r in self.ordenes:
            for m, t in r:
                c[m] += t
        return c

    def cota_inferior(self) -> int:
        """Máximo entre la máquina más cargada y la ruta más larga (cota trivial)."""
        return max(max(self.carga_por_maquina()), max(sum(t for _, t in r) for r in self.ordenes))
