"""Mapa interactivo de incidencias + catastro (Folium / Leaflet).

Construye un HTML autónomo con las incidencias deduplicadas sobre la red de
alcantarillado. Los puntos se colorean y dimensionan por nº de reclamos
(la deduplicación hecha visible); los multi-reclamo llevan el contador y los
críticos pulsan.

Uso típico (ver `notebooks/03_mapa.ipynb`):

    from epsel import mapa
    m = mapa.build_map(gdf)      # gdf = incidencias con catastro (WGS84)
    m.save("reports/mapa_incidencias.html")
"""
from __future__ import annotations

import folium
import geopandas as gpd
import pandas as pd
from folium.plugins import HeatMap

from . import config, io

# Centro aproximado de Chiclayo (WGS84)
CENTRO = (-6.7714, -79.8409)

# Paleta del dashboard (más reclamos = más crítico)
ROJO = "#c23b3b"      # crítica  (>= 3 reclamos)  -> pulsa
AMBAR = "#c47a0f"     # alta     (2 reclamos)
VERDE = "#1d9e75"     # reclamo único

UMBRAL_NUMERO = 2     # a partir de aquí se dibuja el contador encima del punto
UMBRAL_PULSO = 3      # a partir de aquí el punto pulsa (animación)

# CSS de los marcadores animados (se inyecta una vez en el <head> del mapa)
PULSE_CSS = """
<style>
.gota-pt { position: relative; width: 0; height: 0; }
.gota-core {
  position: absolute; transform: translate(-50%, -50%);
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  color: #fff; font: 700 11px/1 -apple-system, system-ui, sans-serif;
  border: 2px solid #fff; box-shadow: 0 1px 3px rgba(0,0,0,.45); z-index: 2;
}
.gota-pulse {
  position: absolute; transform: translate(-50%, -50%);
  border-radius: 50%; z-index: 1;
  animation: gotaPulse 1.8s ease-in-out infinite;
}
@keyframes gotaPulse {
  0%, 100% { opacity: .15; transform: translate(-50%, -50%) scale(.65); }
  50%      { opacity: .40; transform: translate(-50%, -50%) scale(1.15); }
}
</style>"""


# --------------------------------------------------------------------------- #
# Helpers de estilo / contenido
# --------------------------------------------------------------------------- #
def color(n: int) -> str:
    if n >= UMBRAL_PULSO:
        return ROJO
    if n >= UMBRAL_NUMERO:
        return AMBAR
    return VERDE


def div_icon(n: int) -> folium.DivIcon:
    """Marcador estilo dashboard: anillo (pulsa si es crítico) + contador de reclamos."""
    c = color(n)
    size = 20 if n < UMBRAL_PULSO else 24
    pulse_d = 40 if n < UMBRAL_PULSO else 52
    pulse = (f'<div class="gota-pulse" style="width:{pulse_d}px;height:{pulse_d}px;'
             f'background:{c};"></div>') if n >= UMBRAL_PULSO else ""
    html = (f'<div class="gota-pt">{pulse}'
            f'<div class="gota-core" style="width:{size}px;height:{size}px;background:{c};">{n}</div>'
            f'</div>')
    return folium.DivIcon(html=html, icon_size=(0, 0), icon_anchor=(0, 0))


def _txt(v, default="—"):
    return default if pd.isna(v) else v


def _fila(label: str, valor) -> str:
    """Fila del popup solo si el valor existe; si no, cadena vacía."""
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)) or valor == "":
        return ""
    return f"{label}: {valor}<br>"


def popup_html(d: dict) -> str:
    """HTML del popup de una incidencia (omite las líneas sin dato)."""
    red = None
    if pd.notna(d.get("red_diameter")):
        mat = d.get("red_material")
        mat = "" if pd.isna(mat) else f" · {mat}"
        red = f"Ø{int(d['red_diameter'])}{mat} · a {d['red_dist_m']:.0f} m"
    manzana, sector = d.get("manzana"), d.get("sector")
    ubic = f"{_txt(manzana)} · Sector {_txt(sector)}" if (pd.notna(manzana) or pd.notna(sector)) else None
    fecha = d.get("FECHA_PRIMER_RECLAMO")
    fecha = fecha.strftime("%Y-%m-%d") if pd.notna(fecha) else None
    dur = d.get("DURACION_MEDIA_DIAS")
    dur = f"{dur:.0f} d" if pd.notna(dur) else None

    catastro = (_fila("Red alcantarillado", red)
                + _fila("Buzón más cercano", d.get("bz_facilityid"))
                + _fila("Manzana", ubic))
    bloque = f'<hr style="margin:6px 0"><b>Catastro técnico</b><br>{catastro}' if catastro else ""
    dir_txt = d.get("DIRECCION")
    dir_html = f'<div style="color:#555">{dir_txt}</div>' if pd.notna(dir_txt) else ""

    return (f'<div style="font-family:system-ui;font-size:12px;min-width:230px">'
            f'<div style="font-weight:700;color:#c0392b">{_txt(d.get("CATEGORIA_INCIDENCIA"))} '
            f'· {_txt(d.get("TIPO_GRUPO"))}</div>{dir_html}'
            f'<hr style="margin:6px 0"><b>{int(d["N_RECLAMOS"])}</b> reclamo(s) asociado(s)<br>'
            f'{_fila("Primer reclamo", fecha)}{_fila("Días hasta cierre (admin.)", dur)}'
            f'{bloque}</div>')


def _simples_geojson(g: gpd.GeoDataFrame) -> dict:
    """FeatureCollection de las incidencias de 1 reclamo (capa única y liviana)."""
    features = []
    for r in g.itertuples(index=False):
        d = r._asdict()
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [d["LONGITUD"], d["LATITUD"]]},
            "properties": {
                "incidencia": f"{_txt(d.get('CATEGORIA_INCIDENCIA'))} · {_txt(d.get('TIPO_GRUPO'))}",
                "direccion": _txt(d.get("DIRECCION"), "s/dirección"),
            },
        })
    return {"type": "FeatureCollection", "features": features}


def _capa_lineas(gdf, col: str, weight: float, simplify_m=None, dissolve=False):
    """GeoJson de una capa de líneas en WGS84, simplificada y opcionalmente fusionada."""
    g = gdf.to_crs(config.CRS_UTM_17S)
    if simplify_m:
        g["geometry"] = g.simplify(simplify_m)
    if dissolve:
        g = gpd.GeoDataFrame(geometry=[g.union_all()], crs=g.crs)
    g = g.to_crs(config.CRS_WGS84)
    return folium.GeoJson(
        g[["geometry"]].to_json(),
        style_function=lambda _f, c=col, w=weight: {"color": c, "weight": w, "opacity": 0.7},
    )


def _leyenda(m) -> None:
    html = """
    <div style="position:fixed;bottom:24px;left:24px;z-index:9999;background:white;
      padding:10px 14px;border-radius:8px;box-shadow:0 1px 6px rgba(0,0,0,.3);
      font-family:system-ui;font-size:12px">
      <b>Incidencias · nº de reclamos</b><br>
      <span style="color:#1d9e75">●</span> 1 reclamo &nbsp;
      <span style="color:#c47a0f">②</span> 2 &nbsp;
      <span style="color:#c23b3b">③</span> 3+ (pulsa) <br>
      <span style="color:#1565c0">▬</span> Red primaria &nbsp;
      <span style="color:#7e9fbf">▬</span> Red secundaria
    </div>"""
    m.get_root().html.add_child(folium.Element(html))


# --------------------------------------------------------------------------- #
# Construcción del mapa
# --------------------------------------------------------------------------- #
def build_map(gdf: pd.DataFrame, *, con_secundaria: bool = True) -> folium.Map:
    """Arma el mapa Folium completo a partir de las incidencias con catastro.

    `gdf` debe tener LATITUD/LONGITUD/N_RECLAMOS y, opcionalmente, las columnas
    del catastro (`red_*`, `bz_*`, `manzana`, `sector`) para los popups.
    """
    m = folium.Map(location=CENTRO, zoom_start=13, tiles="cartodbpositron", prefer_canvas=True)
    m.get_root().header.add_child(folium.Element(PULSE_CSS))

    # --- catastro (debajo de las incidencias) ---
    fg_prim = folium.FeatureGroup(name="Red primaria (colectores)", show=True)
    _capa_lineas(io.load_layer("redes_primarias"), "#1565c0", 2.5).add_to(fg_prim)
    fg_prim.add_to(m)

    if con_secundaria:
        fg_sec = folium.FeatureGroup(name="Red secundaria", show=False)
        _capa_lineas(io.load_layer("redes_secundarias"), "#7e9fbf", 1,
                     simplify_m=3, dissolve=True).add_to(fg_sec)
        fg_sec.add_to(m)

    # --- incidencias ---
    simples = gdf[gdf["N_RECLAMOS"] < UMBRAL_NUMERO]
    multi = gdf[gdf["N_RECLAMOS"] >= UMBRAL_NUMERO]

    fg_simple = folium.FeatureGroup(name="Incidencias · 1 reclamo", show=True)
    folium.GeoJson(
        _simples_geojson(simples),
        marker=folium.CircleMarker(radius=4, color=VERDE, weight=1,
                                   fill=True, fill_color=VERDE, fill_opacity=0.7),
        popup=folium.GeoJsonPopup(fields=["incidencia", "direccion"],
                                  aliases=["Incidencia", "Dirección"]),
    ).add_to(fg_simple)
    fg_simple.add_to(m)

    fg_multi = folium.FeatureGroup(name="Incidencias · multi-reclamo", show=True)
    for r in multi.itertuples(index=False):
        d = r._asdict()
        folium.Marker(
            location=(d["LATITUD"], d["LONGITUD"]),
            icon=div_icon(int(d["N_RECLAMOS"])),
            popup=folium.Popup(popup_html(d), max_width=280),
        ).add_to(fg_multi)
    fg_multi.add_to(m)

    # --- mapa de calor ---
    fg_heat = folium.FeatureGroup(name="Mapa de calor", show=False)
    HeatMap(gdf[["LATITUD", "LONGITUD"]].values.tolist(), radius=12, blur=18).add_to(fg_heat)
    fg_heat.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    _leyenda(m)
    return m
