"""Configuración central de rutas del proyecto EPSEL-DATATHON.

Importar desde cualquier script/notebook:

    from epsel.config import RAW, PROCESSED, REPORTS, DATA_DICT, CATASTRO

Así ningún script depende del directorio de trabajo desde el que se ejecuta.
"""
from __future__ import annotations

from pathlib import Path

# Raíz del repo = dos niveles arriba de este archivo (src/epsel/config.py)
ROOT = Path(__file__).resolve().parents[2]

# --- Datos -----------------------------------------------------------------
DATA = ROOT / "data"
RAW = DATA / "raw"            # datos originales inmutables
INTERIM = DATA / "interim"    # transformaciones intermedias
PROCESSED = DATA / "processed"  # datasets finales listos para modelar
EXTERNAL = DATA / "external"  # datos de terceros

DANA = RAW / "dana"
CATASTRO = RAW / "catastro"

# --- Salidas ----------------------------------------------------------------
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
DATA_DICT = REPORTS / "data_dictionaries"
MODELS = ROOT / "models"

# --- Sistemas de coordenadas ------------------------------------------------
# Catastro de alcantarillado/manzanas viene en Web Mercator; red de agua en UTM 17S.
CRS_WEB_MERCATOR = "EPSG:3857"
CRS_UTM_17S = "EPSG:32717"   # CRS métrico canónico del proyecto (cruces por distancia)
CRS_WGS84 = "EPSG:4326"      # para mapas web / folium

# --- Rutas concretas de cada dataset ---------------------------------------
TICKETS_XLSX = DANA / "dana-tickets.xlsx"

# Cada capa de catastro: (nombre lógico, ruta al .shp, CRS esperado)
SHAPEFILES = {
    "manzanas": CATASTRO / "geografia" / "SHP.shp",
    "buzones": CATASTRO / "buzones" / "BZ.shp",
    "redes_primarias": CATASTRO / "redes-primarias" / "REDES_PRIMARIAS.shp",
    "redes_secundarias": CATASTRO / "redes-secundarias" / "REDES_SECUNDARIAS.shp",
    # red_agua: el .shp NO llegó (solo .dbf/.prj/.shx). Sin geometría utilizable.
    "red_agua_dbf": CATASTRO / "redes-agua" / "RED_AGUA.dbf",
}


def ensure_dirs() -> None:
    """Crea las carpetas de salida si no existen."""
    for d in (INTERIM, PROCESSED, REPORTS, FIGURES, DATA_DICT, MODELS):
        d.mkdir(parents=True, exist_ok=True)
