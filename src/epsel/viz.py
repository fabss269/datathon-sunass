"""Utilidades de visualización para el EDA (estilo consistente, guardado de figuras)."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # backend sin ventana (headless)
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams.update({
    "figure.dpi": 110,
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

AZUL = "#1F4E78"
NARANJA = "#E07B39"


def savefig(fig, path: Path) -> Path:
    """Guarda la figura ajustada y la cierra."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def barh_counts(series: pd.Series, title: str, top: int = 15,
                color: str = AZUL, pct: bool = True):
    """Barras horizontales con los valores más frecuentes de una serie."""
    vc = series.value_counts(dropna=False).head(top)[::-1]
    total = len(series)
    fig, ax = plt.subplots(figsize=(8, max(3, 0.42 * len(vc))))
    labels = [str(x)[:45] for x in vc.index]
    ax.barh(labels, vc.values, color=color)
    for y, v in enumerate(vc.values):
        txt = f"{v:,}".replace(",", ".")
        if pct:
            txt += f"  ({v/total*100:.1f}%)"
        ax.text(v, y, " " + txt, va="center", fontsize=8)
    ax.set_title(title)
    ax.margins(x=0.18)
    return fig, ax
