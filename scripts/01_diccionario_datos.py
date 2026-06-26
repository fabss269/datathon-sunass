"""Genera un diccionario de datos en Excel por cada dataset del proyecto.

Salida: reports/data_dictionaries/<dataset>.xlsx

Uso:
    uv run python scripts/01_diccionario_datos.py
"""
from __future__ import annotations

from epsel import config, descriptions
from epsel.data_dictionary import build_meta, profile_dataframe, write_dictionary
from epsel.io import load_layer, load_tickets

config.ensure_dirs()

# (nombre, descripciones, fuente, loader)
DATASETS = [
    ("tickets", descriptions.TICKETS, "DANA — export de tickets (reclamos operacionales) 2025",
     load_tickets),
    ("manzanas", descriptions.MANZANAS, "Catastro técnico (GIS) — manzanas Sector 09 (SHP.shp)",
     lambda: load_layer("manzanas")),
    ("buzones", descriptions.BUZONES, "Catastro técnico (GIS) — buzones de alcantarillado (BZ.shp)",
     lambda: load_layer("buzones")),
    ("redes_primarias", descriptions.REDES, "Catastro técnico (GIS) — colectores primarios (REDES_PRIMARIAS.shp)",
     lambda: load_layer("redes_primarias")),
    ("redes_secundarias", descriptions.REDES, "Catastro técnico (GIS) — redes secundarias (REDES_SECUNDARIAS.shp)",
     lambda: load_layer("redes_secundarias")),
    ("red_agua", descriptions.RED_AGUA,
     "Catastro técnico (GIS) — red de agua (RED_AGUA.dbf; SIN geometría .shp)",
     lambda: load_layer("red_agua_dbf")),
]


def main() -> None:
    for name, desc, source, loader in DATASETS:
        df = loader()
        extra = None
        if name == "red_agua":
            extra = {"ADVERTENCIA": "Falta el archivo .shp: la tabla no tiene geometría utilizable."}
        meta = build_meta(name, df, source, extra)
        profile = profile_dataframe(df, desc)
        out = config.DATA_DICT / f"{name}.xlsx"
        write_dictionary(profile, meta, out)
        vac = (profile["Observaciones"].str.contains("VACÍA|Constante", na=False)).sum()
        print(f"[OK] {name:18} {df.shape[0]:>6} filas x {profile.shape[0]:>2} cols  "
              f"({vac} cols vacías/constantes)  -> {out.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
