#!/bin/bash
# Corre todos los experimentos en orden. B0 (parámetros comunes) va primero porque los demás leen sus resultados; B7 (CP-SAT) va al final para que tenga
# la máquina sin otra carga.
cd "$(dirname "$0")"
for s in b0_comunes b1_base b5_reglas b2_ajuste b2d_operador b6_supuestos b3_operadores b8_bits b4_presupuesto b7_exacto; do
  echo "== $s $(date +%H:%M:%S)"
  python3 $s.py || { echo "FALLÓ $s"; exit 1; }
done
echo "TERMINADO $(date +%H:%M:%S)"
