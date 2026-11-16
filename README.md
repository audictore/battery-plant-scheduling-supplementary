# Código y datos de «Codificaciones genéticas, reglas y solucionador exacto para programar una planta de baterías con re-entradas»

Material del artículo «Codificaciones genéticas, reglas y solucionador exacto para programar una planta de baterías con re-entradas», que está en revisión. Aquí está el código de los experimentos, el resultado de cada corrida, el horario de uno de los grupos de la planta y los guiones con los que se arman las tablas y las figuras del texto, para que se pueda ver cómo se hizo todo y repetirlo.

## Para correrlo

```bash
cd experimentos
pip install -r requirements.txt    # además hace falta g++ (C++17)
python3 -m pytest -q pruebas
```

El núcleo en C++ se compila solo la primera vez. Las 24 pruebas tardan unos 20 segundos y no necesitan descargar nada. Las tablas, las cifras del texto y las figuras se rehacen con `python3 -m analisis_jsp.tablas_bat` desde `experimentos/`, y las tablas comparativas completas con `python3 -m analisis_jsp.exportar_tablas`.

## Qué hay en cada carpeta

- `experimentos/jsp_ag/`: el decodificador, las tres codificaciones con sus operadores y la búsqueda aleatoria en C++ (`nucleo.cpp`), su envoltura en Python, las instancias de la planta y sus variantes (`hfs.py`), el modelo de CP-SAT (`exacto_hfs.py`) y el reparto de corridas en procesos.
- `experimentos/b1_…` a `b8_…`: un guion por experimento (ver abajo). `correr_todo.sh` los encadena.
- `experimentos/analisis_jsp/`: referencias, estadística, tablas, figuras, horario y exportación a Excel.
- `experimentos/resultados/`: una fila por corrida (CSV), las curvas de convergencia (NPZ), las configuraciones elegidas (JSON), el horario de G1 (`horario_G1.xlsx`, `horario_G1.json`) y `tablas_comparativas.xlsx`.
- `experimentos/instancias/`: las tablas del conjunto de datos transcritas a JSON.
- `auditoria/`: guiones que recalculan las cifras del texto sin usar el código del estudio y un validador de calendarios escrito aparte.

## Qué experimento es cuál

| Guion | Qué mide | Salida |
|---|---|---|
| `b0_comunes.py` | ajuste de torneo, elitismo, probabilidad de cruza y sigma (dos tandas de rejilla y una confirmación con semillas nuevas) | `B0a_comunes.csv`, `B0b_confirmacion.csv`, `B0_mejor_config.json` |
| `b1_base.py` | tres codificaciones y búsqueda aleatoria, parámetros base, 25 instancias | `B1_base.csv` |
| `b2_ajuste.py` | rejilla de 10 escalas de mutación por 5 poblaciones y mejor celda de cada codificación | `B2a_rejilla.csv`, `B2b_ajustado.csv` |
| `b2d_operador.py` | ajuste propio de binaria con uniforme y llaves con dos puntos | `B2d_*` |
| `b3_operadores.py` | 12 combinaciones de codificación, cruza y código Gray | `B3_operadores.csv` |
| `b4_presupuesto.py` | hasta 300 000 evaluaciones en las cinco instancias originales | `B4_*` |
| `b5_reglas.py` | reglas de despacho SPT, MWKR y MOPNR en los cuatro supuestos | `B5_reglas.csv` |
| `b6_supuestos.py` | los cuatro métodos con los supuestos 1 a 3 del modelo | `B6_supuestos.csv` |
| `b7_exacto.py` | CP-SAT 300 s sin y con solución inicial | `B7_*` |
| `b8_bits.py` | la binaria con 4, 12 y 16 bits por operación | `B8_bits.csv` |

## Cosas que conviene saber

- Cada corrida es determinista si se fija la semilla. Para evaluar se usan las semillas 1000 a 1029 (1000 a 1019 en B4); para ajustar empiezan en 5000 (5013 a 5022 en la confirmación de B0).
- Un sufijo `#n` en el nombre de la instancia (`bat_G3#2`) elige el modo n del decodificador: 1 suma el cambio de familia a la preparación fija, 2 deja adelantar la preparación a la llegada del lote y 3 hace las dos cosas.
- CP-SAT con varios hilos no es determinista: el makespan puede variar y el calendario cambia. Los calendarios que se usaron están en `B7_calendarios.json`.
- Las corridas se repartieron en 7 procesos de una máquina de 8 núcleos, así que los tiempos por corrida no sirven; los de la Sección 2.4 salen de B7, medidos sin otra carga.
- El horario de G1 minimiza el tiempo total y no usa las fechas de entrega del conjunto de datos: dos de los diez lotes terminan tarde. El libro de Excel lo dice en una hoja aparte.
- Versiones: Python 3.14, NumPy, SciPy, pandas, OR-Tools 9.15 y g++ con `-O2`.

## Datos

Las instancias son las del conjunto de Ma, Lin, Jiang, Qi, Wang y Zhang (Mendeley Data, versión 1, 2026, doi:10.17632/x9sssz7jy4.1, licencia CC BY 4.0). El original es un documento de Word; sus tablas están transcritas en `experimentos/instancias/baterias_parametros.json` con `experimentos/extraer_baterias.py`, que lo lee del archivo original (que no se incluye; el JSON guarda su SHA-256). Los grupos G2 a G5 se arman con los conteos por familia y por ruta que da el propio documento; las variantes (`bat_G2v1`, `bat_G3t2`, …) las genera `jsp_ag/hfs.py` con semillas fijas.

## Uso de IA

Parte del código y del texto se hizo con ayuda de un asistente de IA, como se declara en el manuscrito. Los autores revisaron y aprobaron el diseño, los resultados y el texto.

## Licencia

Todavía no tiene. Se le pondrá una licencia abierta cuando termine la revisión del artículo; mientras tanto es solo para que los revisores lo consulten.
