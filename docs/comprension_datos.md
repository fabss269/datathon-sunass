# Comprensión de los datos (CRISP-DM · Fase 2)

Resumen de la fase de **Data Understanding** del proyecto EPSEL. Consolida los
entregables y los hallazgos transversales. Contexto del negocio: [`../CONTEXT.md`](../CONTEXT.md).

## Entregables de esta fase

| Entregable | Ubicación |
|---|---|
| Diccionarios de datos (1 Excel por dataset) | `reports/data_dictionaries/*.xlsx` |
| EDA tickets DANA (informe + 8 figuras) | `reports/eda/tickets.md`, `reports/figures/tickets/` |
| EDA catastro (informe + 5 figuras) | `reports/eda/catastro.md`, `reports/figures/catastro/` |
| Análisis del notebook heredado | `docs/analisis_notebook_lector.md` |
| Código reproducible | `src/epsel/`, `scripts/01_…`, `02_…`, `03_…` |

Reproducir todo:
```bash
uv sync
uv run python scripts/01_diccionario_datos.py
uv run python scripts/02_eda_tickets.py
uv run python scripts/03_eda_catastro.py
```

## Datasets analizados (6)

| Dataset | Filas | Geometría | Aporte principal | Estado |
|---|---|---|---|---|
| tickets (DANA) | 15.141 | ninguna | reclamos: tipo, servicio, tiempo, suministro | Sin coordenadas |
| buzones (BZ) | 21.354 | puntos | nodos + cotas (invert/rimelev) + flujo | Completa y rica |
| manzanas (SHP) | 776 | polígonos | contexto urbano Sector 09 | Completa (1 sector) |
| redes_primarias | 1.793 | líneas | colectores con diámetro/material | Completa |
| redes_secundarias | 29.022 | líneas | red secundaria con diámetro/material | Completa |
| red_agua | 25.403 | **falta .shp** | tabla de tuberías de agua | Sin geometría |

## Hallazgos transversales

1. **El cuello de botella es geolocalizar los tickets.** No hay lat/long; el 73.7% trae
   `SUMINISTRO` (vía de cruce más directa) y 26.3% no es ubicable.
2. **Duplicidad real y medible:** ~21% de los tickets son repeticiones del mismo suministro
   → la deduplicación es una victoria temprana viable hoy.
3. **El catastro de alcantarillado es utilizable**, pero la mayoría de columnas del esquema
   ESRI están vacías/constantes. Lo valioso: geometría + `invert`/`rimelev`/`flowdir` de
   buzones y `diameter`/`material` de redes.
4. **Sin datos de antigüedad/condición** (placeholders 1900/1990) → el modelo de
   supervivencia de tuberías no es viable; se sustituye por un índice de riesgo estructural.
5. **CRS mixtos:** alcantarillado/manzanas en EPSG:3857, red de agua declara EPSG:32717.
   Se unifica todo a **UTM 17S (EPSG:32717)** para medir en metros.
6. **Calidad espacial:** la red cubre varias localidades separadas (no solo Sector 09) y hay
   buzones atípicos lejos del núcleo → depurar antes de cruces espaciales.
7. **Privacidad:** los tickets contienen PII (DNI, celular, nombre) → anonimizar para análisis.

## Siguiente fase (Preparación de datos)
- Tabla de cruce `SUMINISTRO → geometría` (depende de catastro comercial / DANA).
- Pipeline de deduplicación de tickets por suministro + ventana temporal.
- Reconstrucción del grafo dirigido de alcantarillado por geometría + cotas.
- Normalización de `TIPO DE ATENCION` y limpieza de columnas constantes/PII.
