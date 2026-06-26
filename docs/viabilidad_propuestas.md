# Viabilidad de las propuestas — a la luz del análisis de datos

> Basado en la fase de comprensión de datos (`docs/comprension_datos.md`,
> `reports/eda/*`). Viabilidad = % que se puede hacer **hoy** con los datos en mano.

## Tabla resumen

| # | Propuesta | Viabilidad hoy | Bloqueo principal |
|---|---|:---:|---|
| a | Dashboard operativo | 🟡 60% | El mapa necesita coordenadas; la parte tabular está lista |
| b | Deduplicación de incidencias | 🟢 90% | Solo cubre el 74% con suministro |
| c | Clustering geoespacial (HDBSCAN, hot-spots) | 🔴 0% | Coordenadas de tickets |
| d | Grafo dirigido / causa raíz | 🟡 80% | Topología sí; aplicarla a un reclamo real necesita geolocalizarlo |
| e1 | Modelo de supervivencia de tuberías | 🔴 5% | No hay fechas de instalación ni historial de fallas |
| e2 | Regresión del tiempo de resolución | 🟡 50% | Solo hay cierre administrativo, no atención real |
| f | Scoring de criticidad | 🟡 55% | Factores de red/población dependen de geolocalizar |
| g | Aplicación web | 🟢 70% | No es bloqueo de datos; depende de a–f y de la API de DANA |

🟢 listo o casi · 🟡 parcial · 🔴 bloqueado

---

## Detalle por propuesta

### a) Dashboard operativo — 🟡 60%
- **Hoy:** panel de estadísticas (tickets por mes/día/hora, por tipo, servicio, distrito,
  estado), filtros y tablas. Todo demostrado en el EDA.
- **Falta para 100%:** el **mapa con puntos de incidencia** y las alertas por clúster
  necesitan coordenadas de los tickets. Las alertas por *tiempo sin atención* sí salen ya.

### b) Deduplicación — 🟢 90%
- **Hoy:** implementada (`epsel.cleaning.assign_event_ids`). Distingue **duplicado**
  (mismo suministro+servicio en pocos días) de **recurrencia** (mismo punto a lo largo del año).
- **Falta para 100%:** (1) deduplicar también el **26% sin suministro** usando la dirección
  normalizada/geocodificada; (2) **validar la ventana temporal** con Operaciones (¿7 días?).

### c) Clustering geoespacial (HDBSCAN + Getis-Ord / Moran's I) — 🔴 0%
- **Bloqueo total:** sin lat/long de los tickets no hay puntos que agrupar.
- **Falta para 100%:** **coordenadas de los tickets** (ver enablers). La red ya está lista
  para servir de base / corregir el sesgo por densidad.

### d) Grafo dirigido / causa raíz — 🟡 80%
- **Hoy:** el grafo de alcantarillado es **construible** — buzones con `invert` al 100% y
  `flowdir` al 94% permiten reconstruir sentido de flujo aunque `frommh`/`tomh` vengan vacíos
  (CONTEXT reporta 84% de tramos enganchando limpio).
- **Falta para 100%:** (1) **depurar** los buzones atípicos y las 2 geometrías MultiLineString;
  (2) para correr la causa raíz **sobre un reclamo concreto** hay que **geolocalizar ese reclamo**
  (otra vez, coordenadas).

### e1) Supervivencia de tuberías — 🔴 5%
- **Bloqueo de origen:** `installdat`, `condition`, `repairs` vienen vacíos o con placeholder
  (1900/1990). No llegarán (campos vacíos en la fuente).
- **Falta para 100%:** historial de instalación/fallas que **no existe** → se sustituye por un
  **índice de riesgo estructural** (material + diámetro + profundidad + proxies). Viable como índice, no como modelo de supervivencia.

### e2) Regresión del tiempo de resolución — 🟡 50%
- **Hoy:** hay `DURACION_DIAS` y predictores (tipo, servicio, distrito); se puede entrenar.
- **Cuidado:** la fecha de solución es **cierre administrativo**, no atención en campo
  (mediana 10.9 d; agua tarda más que desagüe). El modelo predeciría el target equivocado.
- **Falta para 100%:** **marcas de tiempo reales de atención** (salida/llegada de cuadrilla).

### f) Scoring de criticidad — 🟡 55%
- **Hoy:** factores ya disponibles — tipo de incidencia, alcance, **recurrencia** (del dedup).
- **Falta para 100%:** factores que dependen de geolocalizar: **antigüedad/riesgo de la red**
  del tramo asociado, **clúster de 400 m**, **población afectada** (manzana/INEI) y **tipo de
  establecimiento** (hospital/colegio → capa externa de POIs).

### g) Aplicación web — 🟢 70%
- **No es bloqueo de datos**, es ingeniería; se puede construir el esqueleto ya.
- **Falta para 100%:** el contenido de a–f y la **interoperabilidad con DANA**
  (API/web service la implementa Cañete; plan B: carga batch del Excel).

---

## Lo que falta para llegar al 100% (enablers, por impacto)

1. **Coordenadas de los tickets** — la llave maestra. Desbloquea a(mapa), c, d(aplicado) y
   buena parte de f. Vías: (i) export de DANA con GPS, (ii) **tabla `SUMINISTRO → geometría`**
   del catastro comercial (la más directa, cubre 73.7%), (iii) geocodificar la dirección.
2. **`RED_AGUA.shp`** — desbloquea el lado de agua (38% de tickets) y el análisis de válvulas.
3. **Marcas de tiempo reales de atención** — para la regresión de SLA (e2) y métricas honestas.
4. **Capas externas** — POIs (hospitales/colegios) y población por manzana (INEI) → scoring (f).
5. **Validación operativa** — ventana de deduplicación y pesos de criticidad con Operaciones.
6. **API de DANA (Cañete)** — para producción en vivo; mientras tanto, carga batch del Excel.

## Lectura ejecutiva
Lo que **no depende de nadie externo** ya es viable y conviene blindarlo como MVP-1:
**dashboard tabular + deduplicación + grafo de la red**. Casi todo lo demás cuelga de **un
solo enabler**: las **coordenadas de los tickets**. Conseguir la tabla `SUMINISTRO → geometría`
es la acción de mayor retorno del proyecto.
