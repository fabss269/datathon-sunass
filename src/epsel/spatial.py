"""Unión espacial (space join) entre incidencias y catastro técnico.

Toma las incidencias geocodificadas (puntos lat/long) y las cruza con las capas
de catastro por su ubicación, en UTM 17S (EPSG:32717) para que las distancias
salgan en metros reales:

- `join_polygon`   -> punto en polígono (p.ej. en qué manzana/sector cae).
- `join_nearest`   -> feature más cercano (p.ej. tubería/buzón más próximo) + distancia.

Todas las funciones reciben/devuelven GeoDataFrames, sin efectos colaterales.
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from . import config


def tickets_to_gdf(
    df: pd.DataFrame,
    lat_col: str = "LATITUD",
    lon_col: str = "LONGITUD",
    *,
    solo_validas: bool = True,
) -> gpd.GeoDataFrame:
    """Convierte un DataFrame con lat/long en GeoDataFrame de puntos (WGS84).

    Por defecto conserva solo las filas con coordenada válida (`COORD_VALIDA`),
    o, si esa columna no existe, las que tengan lat y long no nulos.
    """
    d = df.copy()
    if solo_validas and "COORD_VALIDA" in d.columns:
        d = d[d["COORD_VALIDA"].fillna(False)].copy()
    else:
        d = d[d[lat_col].notna() & d[lon_col].notna()].copy()
    geom = gpd.points_from_xy(d[lon_col], d[lat_col])
    return gpd.GeoDataFrame(d, geometry=geom, crs=config.CRS_WGS84)


def join_polygon(
    points: gpd.GeoDataFrame,
    polygons: gpd.GeoDataFrame,
    cols: list[str],
    *,
    predicate: str = "within",
) -> gpd.GeoDataFrame:
    """Agrega a cada punto las columnas `cols` del polígono que lo contiene.

    Reproyecta los polígonos al CRS de los puntos. Si un punto cae en más de un
    polígono (solapes), conserva el primero.
    """
    polys = polygons[[*cols, "geometry"]].to_crs(points.crs)
    joined = gpd.sjoin(points, polys, how="left", predicate=predicate)
    joined = joined[~joined.index.duplicated(keep="first")]
    return joined.drop(columns=["index_right"], errors="ignore")


def join_nearest(
    points: gpd.GeoDataFrame,
    target: gpd.GeoDataFrame,
    cols: list[str],
    *,
    prefix: str,
    max_distance: float | None = None,
) -> gpd.GeoDataFrame:
    """Agrega a cada punto las columnas del feature de `target` más cercano.

    - Las columnas se renombran con `prefix` (p.ej. `red_diameter`).
    - Añade `<prefix>_dist_m`: distancia en metros al feature.
    - Requiere un CRS métrico: ambos se llevan a UTM 17S internamente y el
      resultado se devuelve en el CRS original de `points`.
    """
    crs_orig = points.crs
    pts_m = points.to_crs(config.CRS_UTM_17S)
    tgt_m = target[[*cols, "geometry"]].to_crs(config.CRS_UTM_17S)
    rename = {c: f"{prefix}_{c}" for c in cols}
    tgt_m = tgt_m.rename(columns=rename)

    joined = gpd.sjoin_nearest(
        pts_m, tgt_m, how="left", distance_col=f"{prefix}_dist_m",
        max_distance=max_distance,
    )
    # sjoin_nearest duplica filas ante empates de distancia -> nos quedamos con una.
    joined = joined[~joined.index.duplicated(keep="first")]
    joined = joined.drop(columns=["index_right"], errors="ignore")
    return joined.to_crs(crs_orig)
