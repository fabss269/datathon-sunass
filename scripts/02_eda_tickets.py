"""EDA del dataset de tickets de DANA.

Genera figuras en reports/figures/tickets/ y un informe en reports/eda/tickets.md.

Uso:
    uv run python scripts/02_eda_tickets.py
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from epsel import config
from epsel.io import load_tickets
from epsel.viz import AZUL, NARANJA, barh_counts, savefig

FIGDIR = config.FIGURES / "tickets"
EDADIR = config.REPORTS / "eda"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def main() -> None:
    config.ensure_dirs()
    FIGDIR.mkdir(parents=True, exist_ok=True)
    EDADIR.mkdir(parents=True, exist_ok=True)
    df = load_tickets()
    n = len(df)
    f = {}  # findings

    # ---- 1. Periodo temporal ----
    fr = df["FECHA REGISTRO"]
    f["periodo"] = f"{fr.min():%Y-%m-%d} a {fr.max():%Y-%m-%d}"
    f["n"] = n

    # serie mensual
    por_mes = fr.dt.month.value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar([MESES[m-1] for m in por_mes.index], por_mes.values, color=AZUL)
    ax.set_title("Tickets registrados por mes (2025)")
    ax.set_ylabel("Nº de tickets")
    savefig(fig, FIGDIR / "01_serie_mensual.png")
    f["mes_pico"] = f"{MESES[por_mes.idxmax()-1]} ({por_mes.max()})"
    f["mes_min"] = f"{MESES[por_mes.idxmin()-1]} ({por_mes.min()})"

    # por día de semana y hora
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    dow = fr.dt.dayofweek.value_counts().sort_index()
    axes[0].bar([dias[i] for i in dow.index], dow.values, color=AZUL)
    axes[0].set_title("Tickets por día de la semana")
    hora = fr.dt.hour.value_counts().sort_index()
    axes[1].bar(hora.index, hora.values, color=NARANJA)
    axes[1].set_title("Tickets por hora de registro")
    axes[1].set_xlabel("Hora")
    savefig(fig, FIGDIR / "02_dia_hora.png")

    # ---- 2. Composición ----
    fig, _ = barh_counts(df["TIPO DE ATENCION"], "Tipo de atención (tipología del problema)", top=12)
    savefig(fig, FIGDIR / "03_tipo_atencion.png")

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    for ax, col, title in zip(
        axes, ["TIPO GRUPO", "ALCANCE", "MEDIO RECEPCIÓN"],
        ["Servicio (agua/desagüe)", "Alcance", "Medio de recepción"]):
        vc = df[col].value_counts()
        ax.bar([str(x)[:12] for x in vc.index], vc.values, color=AZUL)
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=30)
    savefig(fig, FIGDIR / "04_composicion.png")
    g = df["TIPO GRUPO"].value_counts(normalize=True) * 100
    f["desague_pct"] = round(g.get("DESAGUE", 0), 1)
    f["agua_pct"] = round(g.get("AGUA", 0), 1)
    a = df["ALCANCE"].value_counts(normalize=True) * 100
    f["general_pct"] = round(a.get("general", 0), 1)
    m = df["MEDIO RECEPCIÓN"].value_counts(normalize=True) * 100
    f["presencial_pct"] = round(m.get("presencial", 0), 1)
    f["telefono_pct"] = round(m.get("telefono", 0), 1)
    f["top_tipo"] = df["TIPO DE ATENCION"].value_counts().head(1)
    f["atoro_pct"] = round(df["TIPO DE ATENCION"].str.contains("ATORO", na=False).mean() * 100, 1)

    # ---- 3. Distribución geográfica ----
    fig, _ = barh_counts(df["DISTRITO"], "Tickets por distrito", top=10)
    savefig(fig, FIGDIR / "05_distrito.png")
    f["chiclayo_pct"] = round((df["DISTRITO"] == "CHICLAYO").mean() * 100, 1)
    f["n_distritos"] = df["DISTRITO"].nunique()

    # ---- 4. Ubicabilidad ----
    con_sum = df["SUMINISTRO"].notna()
    con_dir = df["DIRECCION"].notna()
    no_ubic = ~con_sum & ~con_dir
    f["sum_pct"] = round(con_sum.mean() * 100, 1)
    f["dir_pct"] = round(con_dir.mean() * 100, 1)
    f["no_ubic_n"] = int(no_ubic.sum())
    f["no_ubic_pct"] = round(no_ubic.mean() * 100, 1)
    fig, ax = plt.subplots(figsize=(6, 4))
    cats = ["Con suministro", "Con dirección", "Sin suministro\nni dirección\n(no ubicable)"]
    vals = [con_sum.sum(), con_dir.sum(), no_ubic.sum()]
    cols = [AZUL, AZUL, NARANJA]
    ax.bar(cats, vals, color=cols)
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v/n*100:.1f}%", ha="center", va="bottom")
    ax.set_title("Ubicabilidad de los tickets")
    ax.set_ylabel("Nº de tickets")
    savefig(fig, FIGDIR / "06_ubicabilidad.png")

    # ---- 5. Duración de resolución ----
    dur = df["DURACION_DIAS"]
    f["dur_med"] = round(dur.median(), 1)
    f["dur_mean"] = round(dur.mean(), 1)
    f["dur_p90"] = round(dur.quantile(0.9), 1)
    f["dur_max"] = round(dur.max(), 1)
    f["dur_neg"] = int((dur < 0).sum())
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.hist(dur.clip(upper=60).dropna(), bins=40, color=AZUL)
    ax.axvline(dur.median(), color=NARANJA, ls="--", label=f"Mediana {dur.median():.1f} d")
    ax.set_title("Distribución del tiempo de cierre administrativo (días, recortado a 60)")
    ax.set_xlabel("Días entre registro y cierre")
    ax.legend()
    savefig(fig, FIGDIR / "07_duracion.png")
    dur_tipo = df.groupby("TIPO GRUPO")["DURACION_DIAS"].median()
    f["dur_agua"] = round(dur_tipo.get("AGUA", float("nan")), 1)
    f["dur_desague"] = round(dur_tipo.get("DESAGUE", float("nan")), 1)

    # ---- 6. Señal de deduplicación ----
    sums = df.loc[con_sum, "SUMINISTRO"]
    por_sum = sums.value_counts()
    repetidos = por_sum[por_sum > 1]
    f["sum_unicos"] = int(por_sum.size)
    f["sum_repetidos"] = int(repetidos.size)
    f["tickets_en_repetidos"] = int(repetidos.sum())
    f["max_rep"] = int(por_sum.max())
    f["dedup_pct"] = round((repetidos.sum() - repetidos.size) / n * 100, 1)
    fig, ax = plt.subplots(figsize=(8, 4))
    dist = por_sum.value_counts().sort_index()
    dist = dist[dist.index <= 10]
    ax.bar(dist.index.astype(str), dist.values, color=AZUL)
    ax.set_title("Suministros según nº de tickets asociados (señal de duplicidad)")
    ax.set_xlabel("Nº de tickets del mismo suministro")
    ax.set_ylabel("Nº de suministros")
    savefig(fig, FIGDIR / "08_duplicidad.png")

    # ---- 7. Calidad: constantes / PII / texto libre ----
    constantes = [c for c in df.columns if df[c].nunique(dropna=True) <= 1]
    f["constantes"] = constantes
    f["det_sol_nulo"] = round(df["DETALLE DE SOLUCIÓN"].isna().mean() * 100, 1)
    f["det_sol_nuniq"] = int(df["DETALLE DE SOLUCIÓN"].nunique())

    _write_report(f)
    print(f"[OK] EDA tickets -> {(EDADIR/'tickets.md').relative_to(config.ROOT)}  "
          f"({len(list(FIGDIR.glob('*.png')))} figuras)")


def _write_report(f: dict) -> None:
    top = f["top_tipo"]
    top_name, top_val = top.index[0], int(top.iloc[0])
    md = f"""# EDA — Tickets DANA (reclamos operacionales)

> Generado automáticamente por `scripts/02_eda_tickets.py`. Figuras en `reports/figures/tickets/`.

## 1. Resumen
- **{f['n']:,} tickets**, periodo **{f['periodo']}** (todos en estado *Finalizado*).
- Servicio: **DESAGÜE {f['desague_pct']}%** / AGUA {f['agua_pct']}%.
- Alcance: **general {f['general_pct']}%** / particular {100-f['general_pct']:.1f}%.
- Medio: **presencial {f['presencial_pct']}%** / teléfono {f['telefono_pct']}%.
- Concentración geográfica: **Chiclayo {f['chiclayo_pct']}%** ({f['n_distritos']} distritos en total).

## 2. Estacionalidad y operación
![serie mensual](../figures/tickets/01_serie_mensual.png)

- Mes pico: **{f['mes_pico']}**; mes más bajo: {f['mes_min']}.
- Patrón por día y hora de registro (oficina): ver `02_dia_hora.png`.

## 3. Tipología del problema
![tipo atención](../figures/tickets/03_tipo_atencion.png)

- Tipo dominante: **{top_name}** ({top_val:,} · {top_val/f['n']*100:.1f}%).
- Los **atoros** (colectores/redes/conexión) representan **{f['atoro_pct']}%** de todos los tickets.
- Composición agua/desagüe, alcance y medio: ver `04_composicion.png`.

## 4. Ubicabilidad (bloqueo crítico para mapear)
![ubicabilidad](../figures/tickets/06_ubicabilidad.png)

- Con código de **suministro**: **{f['sum_pct']}%**; con **dirección**: {f['dir_pct']}%.
- **No ubicables** (sin suministro NI dirección): **{f['no_ubic_n']:,} ({f['no_ubic_pct']}%)**.
- ⚠️ El dataset **no tiene coordenadas**. La geolocalización depende de cruzar el
  `SUMINISTRO` contra el catastro comercial, o de geocodificar la dirección.

## 5. Tiempo de resolución (cierre administrativo)
![duración](../figures/tickets/07_duracion.png)

- Mediana **{f['dur_med']} días**, media {f['dur_mean']}, p90 {f['dur_p90']}, máx {f['dur_max']}.
- Por servicio: AGUA {f['dur_agua']} d / DESAGÜE {f['dur_desague']} d (mediana).
- Registros con duración negativa: {f['dur_neg']}.
- ⚠️ Es **cierre administrativo**, no el tiempo real de atención en campo.

## 6. Duplicidad de órdenes (oportunidad de deduplicación)
![duplicidad](../figures/tickets/08_duplicidad.png)

- De {f['sum_unicos']:,} suministros con ticket, **{f['sum_repetidos']:,} tienen más de uno**
  (hasta **{f['max_rep']} tickets** en un mismo suministro).
- Colapsar los duplicados por suministro reduciría ~**{f['dedup_pct']}%** de los registros,
  confirmando el problema "una llamada = una orden".

## 7. Calidad de datos
- **Columnas constantes (sin valor analítico):** {', '.join(f['constantes']) or '—'}.
- **Datos personales (PII):** PERSONA, DNI, CELULAR, TELEFONO FIJO, CORREO → tratar con cuidado / anonimizar.
- `DETALLE DE SOLUCIÓN`: {f['det_sol_nulo']}% nulo y solo {f['det_sol_nuniq']} valores distintos,
  mayormente "ATENDIDA" con muchos errores de tipeo → bajo valor sin normalización.
- `CORREO ELECTRÓNICO`: en la práctica es el correo del **operador**, no del ciudadano.

## Conclusiones para el proyecto
1. **Viable hoy:** dashboard tabular, análisis por tipo/servicio/distrito y **deduplicación** por suministro.
2. **Bloqueado:** mapa/heatmap y clustering hasta resolver coordenadas (cruce por SUMINISTRO es la vía más directa, cubre {f['sum_pct']}%).
3. Descartar del análisis las columnas constantes y normalizar/ignorar los campos de texto libre.
"""
    (EDADIR / "tickets.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
