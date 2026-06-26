# Análisis del notebook `lector_shapefile_sunass_epsel.ipynb`

> Notebook original movido a `notebooks/00_lector_shapefile_referencia.ipynb`.
> Este documento separa **qué reutilizar** y **qué descartar**, y dónde quedó migrada
> la lógica útil dentro del paquete `src/epsel/`.

## Resumen

El notebook fue un **borrador exploratorio en Google Colab** para validar que los
shapefiles se podían leer y cruzar. Cumplió su objetivo, pero **no es reutilizable tal cual**:
depende de Google Drive, reusa variables de forma confusa y tiene celdas rotas. La lógica
que sí vale la pena ya fue extraída a `epsel.io` y `epsel.viz`.

## ✅ Partes ÚTILES (conservar / ya migradas)

| Celda(s) | Qué hace | Estado |
|---|---|---|
| 9, 11 | Cargar shapefile con `gpd.read_file()` y revisar CRS/geometría/columnas | Migrado a `epsel.io.load_layer()` |
| 31 | Reproyectar a **UTM 17S (EPSG:32717)** y calcular áreas reales en m² | Migrado a `epsel.io.to_utm()`. Hallazgo válido: Web Mercator infla el área ~1.4% |
| 37 | Mapa interactivo con `gdf.to_crs(4326).explore()` (folium/OpenStreetMap) | Útil para el dashboard; reutilizar el patrón |
| 22, 33 | `info()` y valores únicos para perfilar columnas | Superado por el EDA (`scripts/03_eda_catastro.py`) y los diccionarios |
| 13 | `sjoin_nearest(manzanas, redes, max_distance=200)` para asociar manzana↔red | Concepto útil (asociar incidencias a red), **pero ver caveats abajo** |
| 38 | Exportar a `.parquet` (comentado) | Buena práctica: guardar lo procesado en `data/processed/` |
| 2 | `pip install geopandas mapclassify folium` | Reemplazado por `uv` (`pyproject.toml`) |

## ❌ Partes a DESCARTAR (no portables o erróneas)

| Celda(s) | Problema |
|---|---|
| 3-4 | `from google.colab import drive` + `drive.mount()` → específico de Colab, no corre en local |
| 7, 11 | Rutas **hardcodeadas** `'/content/drive/MyDrive/SUNASS'` → no portables. Usar `epsel.config` |
| 20 | `NameError: name 'gdf' is not defined` → **celda rota**; el notebook no corre en orden lineal |
| 9 vs 21-24 | La variable `gdf` se **reusa** para manzanas y luego para redes primarias → fuente de confusión y bugs |
| 12, 16, 17 | `list_redes` se **usa en la celda 12 antes de definirse** en la 17; además se imprime una lista de cientos de `nan` (ruido) |
| 25 | `from pandas import pandas as pd` → import incorrecto/confuso (debe ser `import pandas as pd`) |
| 12, 24, 35 | Celdas de ploteo **duplicadas y comentadas** a medias |

## ⚠️ Caveats técnicos del cruce (celda 13)

El `sjoin_nearest(manzanas, redes, max_distance=200)`:

1. **CRS sin reproyectar:** ambas capas están en EPSG:3857 (Web Mercator). El
   `max_distance=200` se interpreta en *metros de Web Mercator*, que **no son metros reales**
   (distorsión ~1.4% en Chiclayo). → Reproyectar a UTM 17S **antes** de cualquier `max_distance`.
2. **Cardinalidad 1:N:** el join pasó de 776 a **890 filas** (una manzana engancha varias redes).
   Hay que decidir una estrategia de agregación (la red más cercana, todas, conteo, etc.).
3. **Muchos `NaN`:** manzanas sin red a <200 m quedan sin asociación → confirma que la capa de
   manzanas (solo Sector 09) y la red **no se solapan del todo** (la red cubre más localidades).

## Recomendación

- Tomar como **insumo** el patrón cargar → reproyectar a UTM → cruzar, ya encapsulado en `epsel.io`.
- **No** seguir desarrollando sobre el notebook original; usar notebooks nuevos en `notebooks/`
  que importen `epsel` y los scripts de `scripts/` para lo reproducible.
- Para asociar **incidencias (tickets) a la red**, el cruce correcto no es manzana↔red sino
  punto-de-incidencia↔red, y eso requiere primero **geolocalizar el ticket** (cruce por
  `SUMINISTRO`), que es el bloqueo principal del proyecto.
