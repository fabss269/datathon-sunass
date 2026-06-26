1# Datathon SUNASS 2026 — EPSEL · Documento de contexto

**Proyecto:** Herramienta de gestión de incidencias operacionales para EPSEL (empresa de agua y saneamiento de Chiclayo, Lambayeque).
**Equipo:** Ivan, Edgar, Fabiana.
**Marco:** Datathon de innovación de SUNASS, financiada por cooperación suiza (programa SECO / SecoSank). Se desarrolla en ~10 EPS; el reto de EPSEL son las incidencias operacionales.
**Plazo:** 1 mes para desarrollar **e implementar**. Presentación de resultados en agosto.

---

## Actores involucrados

| Entidad | Persona | Rol en el proyecto |
|---|---|---|
| SUNASS | Gerald Eilers | Da los lineamientos: exige plan de trabajo, MVPs e implementación en producción |
| SUNASS | Alexandra | Preocupada por el plazo (1 mes es corto) |
| SUNASS (Cami Yaku1) | Vania Tello | Coordinación, interoperabilidad |
| EPSEL | Michel | Gerencia operacional / informática; tiene la descarga de tickets de DANA |
| EPSEL | Alfonso | Indica que existe área de emergencias con data etiquetada como fallos |
| EPSEL | Max Cavero | Participante operativo |
| EPSEL — Área de emergencias | Ing. Josbar | Encargado de la data de roturas/incidencias etiquetada |
| OTASS | María del Carmen Soto Castrillón | Ex-jefa de informática de EPSEL (18 años); mantiene/soporta DANA. Da el contexto real del sistema |
| Catastro Técnico / GIS | Arquitecto Eduardo | Maneja el GIS (ArcGIS Pro / geoportal); entrega las capas geográficas |
| Cañete | René Barrio Nuevo (gerente de administración) | Dueño del sistema DANA; cualquier API/web service depende de él |

---

## Resumen de las reuniones

**1. Kickoff de la Datathon (16 jun) — con SUNASS y EPSEL.**
Edgar y Fabiana presentaron la propuesta de tres capas (dashboard, modelos, app móvil). Feedback clave de Gerald Eilers: proyecto ambicioso pero preocupa el tiempo → exige un **plan de trabajo con cronograma y MVPs incrementales**; cuidado con justificar las predicciones; y lo más importante, la **implementación en las instalaciones de EPSEL** para que funcione independiente del equipo. EPSEL mencionó que tiene ~3-4 años de data en DANA y una descarga de tickets de 2 años disponible. Alfonso señaló el área de emergencias (ing. Josbar) con data ya etiquetada como fallos.

**2. Coordinación del sistema DANA (22 jun) — con OTASS (María del Carmen).**
La reunión que bajó a tierra el proyecto. Puntos centrales:
- **DANA no da acceso a su base de datos.** La data estructurada vive en Cañete. Para evaluar histórico → pedir Excel exportado a EPSEL; para interoperar → pedir el diccionario de datos a Cañete; el **API/web service lo implementa Cañete, no OTASS** (contacto: René Barrio Nuevo).
- **El problema no es la herramienta, es la cultura de registro:** DANA ya puede registrar en campo con GPS y fotos, pero EPSEL no lo usa. Registran en oficina, no en campo → no hay coordenadas reales.
- El **GIS no está integrado con el sistema comercial** en EPSEL; el ERP integrado sigue en desarrollo en OTASS.
- Consejo: no crear otro aplicativo que recargue trabajo → **interoperar** con lo existente; contemplar gestión de riesgos.

**3-5. Reuniones presenciales con el equipo operativo y Catastro.**
Confirmaron desde el terreno todo lo anterior:
- **DANA es un sistema básico:** genera órdenes de trabajo, nada más. No tiene coordenadas. Requiere código de suministro para registrar.
- **Todo el proceso es manual:** se imprime la orden, se atiende en campo, se anota a mano y alguien la re-digita en oficina. Los informes de gestión se hacen a mano.
- **Duplicidad de órdenes confirmada:** mismo problema = muchas órdenes (cada llamada con código distinto genera una).
- **App móvil descartada:** los operarios no usan celular en campo (manos sucias, se cae, se lo roban). Se pivoteó a una **aplicación web complementaria a DANA**.
- **Criterios de criticidad validados y ampliados:** antigüedad de tubería, tiempo sin atender, clúster de 400m, tipo de establecimiento (hospital/colegio), población afectada. Caveat: hoy priorizan más por coyuntura/mediático que por criterio técnico.
- **Catastro no llega a Operaciones:** las redes nuevas no son visibles para el área operativa; piden acceso de solo lectura.
- El arquitecto Eduardo entregó una muestra de capas geográficas (el catastro comercial completo pesa 350 GB).

---

## 1 · Lo que se desea hacer

### Objetivo central
Construir una herramienta que **unifique la información de DANA (reclamos) y Catastro (red)** para gestionar las incidencias operacionales de EPSEL, con el fin último de **acortar los tiempos de atención** (mejor servicio al usuario y evitar multas de SUNASS). No reemplaza a DANA: lo complementa e interopera.

### Funcionalidades propuestas

**a) Dashboard operativo (la base)**
- Mapa interactivo con capas (agua potable, alcantarillado, sectores) y puntos de incidencia.
- Filtros por distrito, tipo, estado y prioridad.
- Panel de estadísticas (incidencias por día/mes, comparación con día anterior, tiempos).
- Sistema de **alertas**: por tiempo sin atención, por antigüedad de red, y por clúster de incidencias.

**b) Deduplicación de incidencias**
- Colapsar las N llamadas de un mismo evento en un único punto (más "rojo" = más afectado), resolviendo el problema de "50 llamadas = 50 órdenes".

**c) Diagnóstico geoespacial**
- Clustering con **HDBSCAN** + medidas de hot-spot (**Getis-Ord, Moran's I**) para detectar zonas calientes corrigiendo el sesgo por densidad poblacional.

**d) Grafo dirigido de la red (causa raíz)**
- Modelar la red de alcantarillado como grafo dirigido para encontrar la **causa raíz** de un atoro: dado un reclamo, identificar qué tramos/buzones están aguas arriba (posible causa) y aguas abajo (posible afectación).

**e) Modelos predictivos**
- **Supervivencia:** predecir en cuánto tiempo va a fallar una tubería (mantenimiento preventivo).
- **Regresión:** predecir el tiempo de resolución de una incidencia (cumplimiento de SLA).

**f) Scoring de criticidad**
- Priorizar incidencias combinando: tipo de incidencia, alcance, recurrencia del punto, antigüedad de la red, tiempo sin atender, clúster (400m), tipo de establecimiento afectado (hospital/colegio) y población afectada.

**g) Aplicación**
- Originalmente una **app móvil** para operarios en campo; tras el feedback operativo se redefinió como **aplicación web** complementaria a DANA.

### Requisitos no funcionales exigidos por SUNASS
- **Plan de trabajo con MVPs incrementales** (uno robusto antes de pasar al siguiente).
- **Implementación en producción en EPSEL**, que funcione independiente del equipo (instalación, APIs para jalar y cruzar la información).
- Justificación rigurosa de las predicciones.
- Considerar gestión de riesgos.

---

## 2 · Lo que se tiene

### A) Datos de reclamos — `tickets` (export de DANA)

| Atributo | Valor |
|---|---|
| Registros | **15,141 tickets** (todo el año 2025) |
| Estado | Todos "Finalizado" |
| Reparto | DESAGUE 62% / AGUA 38% · ALCANCE general 78% / particular 22% |
| Tipo dominante | Atoro en colectores/desborde 43%, fuga en acometida 16% |
| Medio | Presencial 60% / teléfono 39% |
| **Coordenadas** | **No tiene** (ninguna columna lat/long) |
| Suministro | Presente en **73.7%** (26.3% sin suministro ni dirección → no ubicable) |
| Tiempo de resolución | Mediana ~11 días (es cierre administrativo, no atención real) |

### B) Capas geográficas (Catastro) recibidas

| Capa | Contenido | Estado |
|---|---|---|
| Manzanas (`SHP`) | 776 polígonos, Sector 09 de Chiclayo, EPSG:3857 | Completa |
| Buzones (`BZ`) | 21,354 nodos de alcantarillado, con cota de fondo (`invert`, 100%), cota de tapa, profundidad, dirección de flujo (94%); EPSG:3857 | Completa |
| Redes primarias (`REDES_PRIMARIAS`) | 1,793 colectores (líneas), con diámetro y material; EPSG:3857 | Completa |
| Redes secundarias (`REDES_SECUNDARIAS`) | 29,022 tramos (líneas), con diámetro y material; EPSG:3857 | Completa |
| Red de agua (`RED_AGUA`) | 25,403 tramos, atributos (diámetro 100%, material 99%); EPSG:32717 | **Incompleta: falta la geometría `.shp`** |

Notas técnicas:
- **CRS mixtos:** buzones, redes de alcantarillado y manzanas en EPSG:3857; red de agua en EPSG:32717 (UTM 17S). Se reproyecta todo a UTM 17S para cruces métricos.
- Los campos `frommh`/`tomh` (conexión buzón-a-buzón) y `upelev`/`downelev` de las redes **vienen vacíos** → la topología se reconstruye por geometría + cota.
- Campos de antigüedad y fallas (`installdat`, `condition`, `repairs`, `obstructio`) **vacíos o placeholder** en las tres capas.

### C) Estado de viabilidad de cada propuesta

| Propuesta | Estado | Detalle |
|---|---|---|
| Dashboard tabular | Viable hoy | Solo con los tickets |
| Deduplicación | Viable hoy | Sobre el 74% con suministro |
| Visualizar red de alcantarillado | Viable hoy | Buzones + primarias + secundarias |
| **Grafo dirigido / causa raíz** | **Viable** | Reconstruido por geometría + cota; 84% de tramos enganchan limpio con buzones (20,147 nodos, 25,312 aristas) |
| Scoring de criticidad | Parcial | Base (tipo/alcance/recurrencia) ya; factor de red al geolocalizar; antigüedad reemplazada por riesgo estructural |
| Mapa / heatmap de incidencias | Bloqueado | La red está lista, pero los **tickets no tienen coordenadas** |
| Clustering (HDBSCAN) + hot-spots | Bloqueado | Depende de coordenadas de tickets |
| Visualizar red de agua / análisis de válvulas | Bloqueado | Falta el `RED_AGUA.shp` |
| Supervivencia de tuberías | No viable | Sin fechas de instalación ni historial de fallas → reemplazado por índice de riesgo estructural |

### D) Entregables ya producidos
- Notebook completo para Colab (`pipeline_datathon_epsel.ipynb`): limpieza, análisis, los modelos y visualización.
- Diagrama de Gantt del plan de un mes (22 jun – 19 jul), dividido en Desarrollo (sem 1-2) y Despliegue y pruebas (sem 3-4).
- Proyecto en Jira (espacio **GOTA**) con 26 actividades + 6 hitos cargados con fechas.
- Mapa de la red de alcantarillado integrada (Chiclayo).

---

## Bloqueos pendientes (en orden de impacto)

1. **Coordenadas de los tickets** (lo crítico). Sin lat/long no se puede mapear incidencias, ni correr clustering, ni aplicar la causa raíz a un reclamo real. Opciones: que DANA las exporte, una tabla suministro→geometría, o geocodificar la dirección.
2. **`RED_AGUA.shp`.** Sin la geometría no se mapea la red de agua ni se analizan válvulas. Solo afecta el lado de agua potable (38% de tickets), no el alcantarillado.
3. **Datos de antigüedad/fallas.** No llegarán (campos vacíos en origen) → se sustituye el modelo de supervivencia por un índice de riesgo estructural.
4. **API de DANA.** Depende de Cañete (René Barrio Nuevo); riesgo de no llegar en el mes → plan B: carga batch del Excel.

## Próximos pasos sugeridos
- Solicitud formal de datos a Cañete (coordenadas/diccionario/API), Michel (histórico) y Eduardo (RED_AGUA.shp + redes faltantes).
- Contactar al ing. Josbar (área de emergencias) por la data etiquetada como fallos.
- Validar criterios de criticidad reales con Operaciones.
- Definir el MVP del mes priorizando lo viable hoy (dashboard + deduplicación + grafo) y dejar lo geo-dependiente listo para activarse con coordenadas.
