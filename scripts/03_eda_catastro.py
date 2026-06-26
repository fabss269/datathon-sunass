"""EDA de las capas de catastro (GIS): buzones, manzanas, redes y red de agua.

Genera figuras en reports/figures/catastro/ y un informe en reports/eda/catastro.md.

Uso:
    uv run python scripts/03_eda_catastro.py
"""
from __future__ import annotations

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np

from epsel import config
from epsel.io import load_layer, to_utm
from epsel.viz import AZUL, NARANJA, savefig

FIGDIR = config.FIGURES / "catastro"
EDADIR = config.REPORTS / "eda"


def usable_columns(gdf) -> tuple[int, int]:
    """(columnas con información, total de columnas no geométricas)."""
    cols = [c for c in gdf.columns if c != "geometry"]
    usables = [c for c in cols if gdf[c].notna().any() and gdf[c].nunique(dropna=True) > 1]
    return len(usables), len(cols)


def main() -> None:
    config.ensure_dirs()
    FIGDIR.mkdir(parents=True, exist_ok=True)
    EDADIR.mkdir(parents=True, exist_ok=True)
    f = {}

    manzanas = to_utm(load_layer("manzanas"))
    buzones = to_utm(load_layer("buzones"))
    primarias = to_utm(load_layer("redes_primarias"))
    secundarias = to_utm(load_layer("redes_secundarias"))
    red_agua = load_layer("red_agua_dbf")  # solo tabla, sin geometría

    for name, g in [("manzanas", manzanas), ("buzones", buzones),
                    ("redes_primarias", primarias), ("redes_secundarias", secundarias),
                    ("red_agua", red_agua)]:
        u, t = usable_columns(g)
        f[f"{name}_n"] = len(g)
        f[f"{name}_use"] = u
        f[f"{name}_tot"] = t

    # ---- 1. Mapa integrado de la red de alcantarillado (zoom al núcleo) ----
    # Recorte al 1-99 pct de los buzones para evitar outliers espaciales lejanos.
    bx, by = buzones.geometry.x, buzones.geometry.y
    x0, x1 = np.percentile(bx, [1, 99])
    y0, y1 = np.percentile(by, [1, 99])
    fig, ax = plt.subplots(figsize=(11, 11))
    manzanas.plot(ax=ax, facecolor="#EFEFEF", edgecolor="#CFCFCF", linewidth=0.3)
    secundarias.plot(ax=ax, color="#9DB7CF", linewidth=0.3, label="Redes secundarias")
    primarias.plot(ax=ax, color=AZUL, linewidth=0.9, label="Colectores primarios")
    buzones.plot(ax=ax, color=NARANJA, markersize=1, label="Buzones")
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_title("Red de alcantarillado EPSEL (Chiclayo) — núcleo · UTM 17S")
    ax.legend(loc="upper right", markerscale=6, framealpha=0.9)
    ax.set_axis_off()
    savefig(fig, FIGDIR / "09_red_alcantarillado.png")

    # outliers espaciales
    fuera = ((bx < x0 - 5000) | (bx > x1 + 5000) | (by < y0 - 5000) | (by > y1 + 5000)).sum()
    f["buzones_outliers"] = int(fuera)

    # ---- 2. Diámetros y materiales (redes secundarias) ----
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    d = secundarias["diameter"].replace(0, np.nan).dropna()
    axes[0].hist(d.clip(upper=600), bins=30, color=AZUL)
    axes[0].set_title("Diámetro de redes secundarias (mm)")
    axes[0].set_xlabel("mm")
    mat = secundarias["material"].value_counts()
    axes[1].bar([str(x) for x in mat.index], mat.values, color=AZUL)
    axes[1].set_title("Material (redes secundarias)")
    for i, v in enumerate(mat.values):
        axes[1].text(i, v, f"{v/len(secundarias)*100:.0f}%", ha="center", va="bottom", fontsize=8)
    savefig(fig, FIGDIR / "10_diametros_materiales.png")
    f["mat_top"] = f"{mat.index[0]} ({mat.iloc[0]/len(secundarias)*100:.0f}%)"
    f["diam_med"] = round(float(d.median()), 0)

    # ---- 3. Buzones: cota e hidráulica ----
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    cut = buzones["cutdepth"].replace(0, np.nan).dropna()
    axes[0].hist(cut.clip(upper=10), bins=30, color=AZUL)
    axes[0].axvline(cut.median(), color=NARANJA, ls="--", label=f"Mediana {cut.median():.1f} m")
    axes[0].set_title("Profundidad de buzones (cutdepth, m)")
    axes[0].legend()
    axes[1].scatter(buzones["invert"], buzones["rimelev"], s=2, alpha=0.3, color=AZUL)
    axes[1].set_title("Cota de fondo (invert) vs cota de tapa (rimelev)")
    axes[1].set_xlabel("invert (m)")
    axes[1].set_ylabel("rimelev (m)")
    savefig(fig, FIGDIR / "11_buzones_cotas.png")
    f["cut_med"] = round(float(cut.median()), 1)
    f["flowdir_pct"] = round(buzones["flowdir"].notna().mean() * 100, 1)
    f["invert_pct"] = round(buzones["invert"].notna().mean() * 100, 1)

    # ---- 4. Completitud por capa ----
    fig, ax = plt.subplots(figsize=(9, 4))
    names = ["manzanas", "buzones", "redes_primarias", "redes_secundarias", "red_agua"]
    use = [f[f"{nm}_use"] for nm in names]
    tot = [f[f"{nm}_tot"] for nm in names]
    pos = np.arange(len(names))
    ax.bar(pos, tot, color="#D9D9D9", label="Columnas totales")
    ax.bar(pos, use, color=AZUL, label="Columnas con información")
    ax.set_xticks(pos)
    ax.set_xticklabels(names, rotation=20)
    for i in range(len(names)):
        ax.text(i, tot[i], f"{use[i]}/{tot[i]}", ha="center", va="bottom", fontsize=8)
    ax.set_title("Riqueza de atributos por capa (no vacíos ni constantes)")
    ax.legend()
    savefig(fig, FIGDIR / "12_completitud.png")

    # ---- 5. Manzanas: áreas reales ----
    manzanas = manzanas.copy()
    manzanas["area_m2"] = manzanas.geometry.area
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(manzanas["area_m2"].clip(upper=15000), bins=30, color=AZUL)
    ax.set_title("Área de manzanas (m², UTM 17S, recortado a 15.000)")
    ax.set_xlabel("m²")
    savefig(fig, FIGDIR / "13_manzanas_area.png")
    f["area_total_km2"] = round(manzanas["area_m2"].sum() / 1e6, 2)
    f["area_med"] = round(float(manzanas["area_m2"].median()), 0)

    # CRS y geometrías
    f["crs_alcant"] = "EPSG:3857 (Web Mercator)"
    f["sec_multi"] = int((secundarias.geom_type == "MultiLineString").sum())

    _write_report(f)
    print(f"[OK] EDA catastro -> {(EDADIR/'catastro.md').relative_to(config.ROOT)}  "
          f"({len(list(FIGDIR.glob('*.png')))} figuras)")


def _write_report(f: dict) -> None:
    md = f"""# EDA — Catastro técnico (capas GIS)

> Generado automáticamente por `scripts/03_eda_catastro.py`. Figuras en `reports/figures/catastro/`.
> Todas las capas se reproyectan a **UTM 17S (EPSG:32717)** para medir en metros.

## 1. Inventario de capas
| Capa | Registros | Geometría | CRS origen | Columnas con info / total |
|---|---|---|---|---|
| manzanas | {f['manzanas_n']:,} | Polígonos | EPSG:3857 | {f['manzanas_use']}/{f['manzanas_tot']} |
| buzones | {f['buzones_n']:,} | Puntos | EPSG:3857 | {f['buzones_use']}/{f['buzones_tot']} |
| redes_primarias | {f['redes_primarias_n']:,} | Líneas | EPSG:3857 | {f['redes_primarias_use']}/{f['redes_primarias_tot']} |
| redes_secundarias | {f['redes_secundarias_n']:,} | Líneas | EPSG:3857 | {f['redes_secundarias_use']}/{f['redes_secundarias_tot']} |
| red_agua | {f['red_agua_n']:,} | **SIN .shp** | EPSG:32717 (decl.) | {f['red_agua_use']}/{f['red_agua_tot']} |

## 2. Red de alcantarillado integrada
![red](../figures/catastro/09_red_alcantarillado.png)

- Manzanas + colectores primarios + redes secundarias + buzones, alineados en UTM 17S.
- ⚠️ **{f['buzones_outliers']} buzones** caen muy lejos del núcleo urbano (posibles errores de
  digitalización / coordenadas atípicas) → revisar antes de cálculos espaciales.

## 3. Atributos físicos de la red (redes secundarias)
![diam](../figures/catastro/10_diametros_materiales.png)

- Material predominante: **{f['mat_top']}**.
- Diámetro mediano: **{f['diam_med']:.0f} mm**.

## 4. Buzones: cota e hidráulica (clave para la topología)
![buzones](../figures/catastro/11_buzones_cotas.png)

- `invert` (cota de fondo) presente en **{f['invert_pct']}%** y `flowdir` (dir. de flujo) en {f['flowdir_pct']}%.
- Profundidad mediana de excavación: **{f['cut_med']} m**.
- Estas cotas permiten **reconstruir la topología y el sentido del flujo** del grafo de
  alcantarillado pese a que `frommh`/`tomh` vengan vacíos en las redes.

## 5. Manzanas (Sector 09)
![manzanas](../figures/catastro/13_manzanas_area.png)

- Área total ≈ **{f['area_total_km2']} km²**, área mediana por manzana ≈ {f['area_med']:.0f} m².
- Solo se entregó el **Sector 09**; el catastro completo pesa ~350 GB.

## 6. Riqueza de atributos y calidad
![completitud](../figures/catastro/12_completitud.png)

- La mayoría de columnas del esquema ESRI vienen **vacías o constantes** ('Desconocido', 0).
- Campos de **antigüedad/fallas** (`installdat`, `condition`, `repairs`) vacíos o con
  placeholder (1900/1990) → **no sirven** para modelos de supervivencia de tuberías.
- `red_agua` solo tiene la **tabla .dbf** (sin geometría .shp): no se puede mapear ni
  analizar válvulas hasta recibir el shapefile. Su esquema es ArcGIS Utility Network
  (códigos numéricos en material/networktyp), distinto al de alcantarillado.
- {f['sec_multi']} geometrías de redes secundarias son MultiLineString (revisar al construir el grafo).

## Conclusiones para el proyecto
1. **Viable hoy:** visualizar la red de alcantarillado (buzones + primarias + secundarias) y
   reconstruir el **grafo dirigido** usando geometría + cotas de buzón.
2. **Bloqueado:** red de agua (falta `.shp`) y todo modelo basado en antigüedad/condición.
3. **Acción de calidad:** depurar los buzones atípicos y unificar CRS a UTM 17S antes de cruzar con tickets.
"""
    (EDADIR / "catastro.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
