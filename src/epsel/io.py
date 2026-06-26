"""Carga de datasets del proyecto, con las correcciones de tipo conocidas.

Centraliza la lectura para que notebooks y scripts no repitan parches
(p.ej. la conversión de FECHA SOLUCION, que viene como serial de Excel).
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from . import config

# Excel guarda fechas como nº de días desde 1899-12-30
_EXCEL_EPOCH = "1899-12-30"


def load_tickets(parse_dates: bool = True) -> pd.DataFrame:
    """Carga los tickets de DANA con las fechas ya normalizadas.

    - FECHA REGISTRO ya viene como datetime.
    - FECHA SOLUCION viene como número serial de Excel (float) -> se convierte.
    - Añade columna `DURACION_DIAS` = FECHA SOLUCION - FECHA REGISTRO.
    """
    df = pd.read_excel(config.TICKETS_XLSX)
    if parse_dates:
        df["FECHA REGISTRO"] = pd.to_datetime(df["FECHA REGISTRO"], errors="coerce")
        df["FECHA SOLUCION"] = pd.to_datetime(
            df["FECHA SOLUCION"], unit="D", origin=_EXCEL_EPOCH, errors="coerce"
        )
        df["DURACION_DIAS"] = (
            df["FECHA SOLUCION"] - df["FECHA REGISTRO"]
        ).dt.total_seconds() / 86400
    return df


def load_layer(name: str) -> gpd.GeoDataFrame | pd.DataFrame:
    """Carga una capa de catastro por su nombre lógico (ver config.SHAPEFILES).

    Devuelve GeoDataFrame si hay geometría; DataFrame si es solo tabla
    (caso `red_agua_dbf`, al que le falta el .shp).
    """
    path = config.SHAPEFILES[name]
    return gpd.read_file(path)


def to_utm(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Reproyecta a UTM 17S (EPSG:32717), el CRS métrico canónico del proyecto."""
    return gdf.to_crs(config.CRS_UTM_17S)
