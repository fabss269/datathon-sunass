"""Limpieza y preparación de los tickets de DANA (CRISP-DM · fase 3).

Funciones puras y testeables que el notebook `notebooks/01_preparacion_tickets.ipynb`
aplica paso a paso. Cada función recibe y devuelve un DataFrame, sin efectos colaterales.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

import pandas as pd

# Columnas constantes (1 solo valor) -> sin valor analítico
COLUMNAS_CONSTANTES = ["GRUPO", "CATEGORÍA", "ESTADO DEL TICKET"]

# Datos personales (PII) -> se separan del dataset analítico
COLUMNAS_PII = ["PERSONA", "DNI", "CELULAR", "TELEFONO FIJO",
                "CORREO ELECTRÓNICO", "PARENTESCO"]


# --------------------------------------------------------------------------- #
# Normalización de texto
# --------------------------------------------------------------------------- #
def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _norm(s) -> str | None:
    """Mayúsculas, sin acentos, sin puntuación extra, espacios colapsados."""
    if pd.isna(s):
        return None
    s = _strip_accents(str(s)).upper().strip()
    s = re.sub(r"[.\s]+", " ", s).strip()
    return s or None


# --------------------------------------------------------------------------- #
# 1. Selección de columnas
# --------------------------------------------------------------------------- #
def drop_constant_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Elimina las columnas constantes (sin variabilidad)."""
    presentes = [c for c in COLUMNAS_CONSTANTES if c in df.columns]
    return df.drop(columns=presentes)


def split_pii(df: pd.DataFrame, id_col: str = "TICKET") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa el dataset en (analítico_sin_PII, tabla_PII).

    El dataset analítico conserva un `PERSONA_HASH` (DNI hasheado) que permite
    medir recurrencia por persona sin exponer el dato personal.
    """
    pii_cols = [c for c in COLUMNAS_PII if c in df.columns]
    analitico = df.drop(columns=pii_cols).copy()
    if "DNI" in df.columns:
        analitico["PERSONA_HASH"] = df["DNI"].apply(_hash_dni)
    tabla_pii = df[[id_col, *pii_cols]].copy()
    return analitico, tabla_pii


def _hash_dni(dni) -> str | None:
    if pd.isna(dni):
        return None
    return hashlib.sha1(str(int(dni)).encode()).hexdigest()[:12]


# --------------------------------------------------------------------------- #
# 2. Normalización de categóricas
# --------------------------------------------------------------------------- #
def normalize_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza las columnas categóricas de texto (mayúsculas, sin acentos)."""
    df = df.copy()
    for col in ["ALCANCE", "MEDIO RECEPCIÓN", "DISTRITO", "TIPO GRUPO", "TIPO DE ATENCION"]:
        if col in df.columns:
            df[col] = df[col].map(_norm)
    return df


_CATEGORIA_PATRONES = [
    ("ATORO", r"ATORO"),
    ("FUGA", r"FUGA"),
    ("FALTA_AGUA", r"FALTA DE AGUA"),
    ("BAJA_PRESION", r"BAJA PRESION"),
    ("TAPA_BUZON", r"TAPA"),
    ("ROTURA", r"ROTURA"),
    ("INSPECCION", r"INSPECCION|VERIFICACION"),
    ("CALIDAD", r"CALIDAD|LABORATORIO|DESINFECCION"),
    ("REPARACION", r"REPARACION|OBRAS"),
]


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega variables derivadas útiles para el análisis."""
    df = df.copy()
    # categoría macro de incidencia a partir de TIPO DE ATENCION
    tipo = df["TIPO DE ATENCION"].fillna("")
    cat = pd.Series("OTROS", index=df.index)
    for etiqueta, patron in _CATEGORIA_PATRONES:
        cat = cat.mask(tipo.str.contains(patron, regex=True) & cat.eq("OTROS"), etiqueta)
    df["CATEGORIA_INCIDENCIA"] = cat
    # ubicabilidad
    df["UBICABLE"] = df["SUMINISTRO"].notna() | df["DIRECCION"].notna()
    df["TIENE_SUMINISTRO"] = df["SUMINISTRO"].notna()
    # campos de tiempo
    df["ANIO_MES"] = df["FECHA REGISTRO"].dt.to_period("M").astype(str)
    return df


_SOLUCION_PATRONES = [
    ("ATENDIDA", r"^(?:AT|AE|SE AT)"),     # ATENDIDA, ATENDIDO, ATENIDIDO, AENDIDA, SE ATENDIO...
    ("FINALIZADO", r"FINAL"),
    ("SOLUCIONADO", r"SOLUC"),
]


def normalize_solucion(df: pd.DataFrame, col: str = "DETALLE DE SOLUCIÓN") -> pd.DataFrame:
    """Colapsa el texto libre de cierre (con muchos typos) en un estado canónico."""
    df = df.copy()
    norm = df[col].map(_norm)
    estado = pd.Series("SIN_DETALLE", index=df.index)
    estado = estado.mask(norm.notna(), "OTRO")
    for etiqueta, patron in _SOLUCION_PATRONES:
        estado = estado.mask(norm.notna() & norm.str.contains(patron, regex=True)
                             & estado.isin(["OTRO"]), etiqueta)
    df["ESTADO_SOLUCION"] = estado
    return df


# --------------------------------------------------------------------------- #
# 3. Deduplicación de eventos (varias órdenes = un mismo evento)
# --------------------------------------------------------------------------- #
def assign_event_ids(df: pd.DataFrame, window_days: int = 7) -> pd.DataFrame:
    """Asigna `EVENTO_ID`: agrupa tickets del mismo suministro y servicio
    registrados dentro de una ventana temporal (`window_days`).

    Los tickets sin suministro no se pueden agrupar -> cada uno es su propio evento.
    """
    df = df.copy()
    win = pd.Timedelta(days=window_days)
    df = df.sort_values(["SUMINISTRO", "TIPO GRUPO", "FECHA REGISTRO"])

    grupos = df.groupby(["SUMINISTRO", "TIPO GRUPO"], sort=False)
    prev = grupos["FECHA REGISTRO"].shift()
    nuevo_cluster = prev.isna() | ((df["FECHA REGISTRO"] - prev) > win)
    # cumsum por grupo; los tickets sin suministro quedan NaN -> se rellenan (se enmascaran luego)
    cum = nuevo_cluster.groupby([df["SUMINISTRO"], df["TIPO GRUPO"]]).cumsum().fillna(0).astype(int)

    evento = (df["SUMINISTRO"].astype("Int64").astype(str) + "|"
              + df["TIPO GRUPO"].astype(str) + "|" + cum.astype(str))
    # tickets sin suministro: evento propio por ticket
    sin_sum = df["SUMINISTRO"].isna()
    evento = evento.mask(sin_sum, "T" + df["TICKET"].astype(str))
    df["EVENTO_ID"] = evento
    df["N_RECLAMOS_EVENTO"] = df.groupby("EVENTO_ID")["TICKET"].transform("size")
    return df.sort_values("TICKET")


def collapse_to_events(df: pd.DataFrame) -> pd.DataFrame:
    """Colapsa los tickets a un registro por EVENTO_ID (incidencia única)."""
    agg = {
        "TICKET": ("TICKET", "first"),
        "N_RECLAMOS": ("TICKET", "size"),
        "SUMINISTRO": ("SUMINISTRO", "first"),
        "DIRECCION": ("DIRECCION", "first"),
        "DISTRITO": ("DISTRITO", "first"),
        "TIPO_GRUPO": ("TIPO GRUPO", "first"),
        "CATEGORIA_INCIDENCIA": ("CATEGORIA_INCIDENCIA", "first"),
        "FECHA_PRIMER_RECLAMO": ("FECHA REGISTRO", "min"),
        "FECHA_ULTIMO_RECLAMO": ("FECHA REGISTRO", "max"),
        "DURACION_MEDIA_DIAS": ("DURACION_DIAS", "mean"),
    }
    # arrastra coordenadas si ya fueron geocodificadas
    for col in ("LATITUD", "LONGITUD", "COORD_VALIDA"):
        if col in df.columns:
            agg[col] = (col, "first")
    eventos = df.groupby("EVENTO_ID").agg(**agg).reset_index()
    return eventos.sort_values("N_RECLAMOS", ascending=False)
