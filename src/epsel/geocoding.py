"""Geocodificación de direcciones (dirección -> latitud/longitud).

Soporta dos proveedores (intercambiables con el parámetro `provider`):

- **"google"** (recomendado): Google Maps Geocoding API. Mejor cobertura de direcciones
  peruanas (numeración + urbanizaciones informales). Requiere API key con facturación,
  pero Google da ~$200 USD/mes de crédito gratis (≈ 40.000 geocodificaciones) -> nuestras
  ~8.000 direcciones entran gratis. La key se lee del argumento `api_key` o de la variable
  de entorno `GOOGLE_MAPS_API_KEY`.
- **"nominatim"** (gratis, sin key): OpenStreetMap. Límite de 1 consulta/seg y **menor
  cobertura** de direcciones informales; usa una cascada dirección->barrio para paliar.

Características comunes: caché en disco (no re-consulta lo ya resuelto), validación de que
la coordenada caiga en Lambayeque, y una etiqueta de `precision` por resultado.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import GoogleV3, Nominatim

# Bounding box aproximado de la región Lambayeque (lat_min, lat_max, lon_min, lon_max)
BBOX_LAMBAYEQUE = (-7.30, -5.45, -80.95, -79.10)

SUFIJO_DEFECTO = ", Chiclayo, Lambayeque, Perú"
_CACHE_COLS = ["direccion", "lat", "lon", "precision"]


def en_bbox(lat, lon, bbox: tuple = BBOX_LAMBAYEQUE) -> bool:
    """True si (lat, lon) cae dentro del bounding box dado."""
    if lat is None or lon is None or pd.isna(lat) or pd.isna(lon):
        return False
    lat_min, lat_max, lon_min, lon_max = bbox
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def limpiar_direccion(d: str) -> str:
    """Normaliza referencias de manzana/lote y colapsa espacios (para Nominatim)."""
    d = re.sub(r"\bMZ\.?\s*\S+|\bLT\.?\s*\S+", "", d, flags=re.I)
    return re.sub(r"\s+", " ", d).strip()


# --------------------------------------------------------------------------- #
# Caché
# --------------------------------------------------------------------------- #
def _load_cache(path: Path) -> dict[str, tuple]:
    if path.exists():
        c = pd.read_csv(path)
        if "precision" not in c.columns:
            c["precision"] = None
        return {r.direccion: (r.lat, r.lon, r.precision) for r in c.itertuples()}
    return {}


def _save_cache(cache: dict[str, tuple], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [(d, *vals) for d, vals in cache.items()], columns=_CACHE_COLS,
    ).to_csv(path, index=False, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Resolución de una dirección según proveedor
# --------------------------------------------------------------------------- #
def _resolver_google(geocode, direccion: str, sufijo: str) -> tuple:
    """Google maneja bien la dirección completa; la precisión sale de location_type."""
    loc = geocode(f"{direccion}{sufijo}", region="pe")
    if loc and en_bbox(loc.latitude, loc.longitude):
        lt = (loc.raw.get("geometry", {}) or {}).get("location_type", "")
        return (loc.latitude, loc.longitude, f"google:{lt or 'OK'}")
    return (None, None, None)


def _resolver_nominatim(geocode, direccion: str, sufijo: str) -> tuple:
    """Cascada: dirección limpia -> urbanización/barrio (primeras 2 palabras)."""
    limpia = limpiar_direccion(direccion)
    barrio = " ".join(limpia.split()[:2])
    intentos = []
    if limpia:
        intentos.append((f"{limpia}{sufijo}", "osm:exacta"))
    if barrio and barrio != limpia:
        intentos.append((f"{barrio}{sufijo}", "osm:barrio"))
    for query, precision in intentos:
        loc = geocode(query)
        if loc and en_bbox(loc.latitude, loc.longitude):
            return (loc.latitude, loc.longitude, precision)
    return (None, None, None)


def _build_geocoder(provider: str, api_key: str | None, min_delay: float):
    """Devuelve (funcion_geocode_rate_limited, resolver, min_delay_efectivo)."""
    if provider == "google":
        key = api_key or os.environ.get("GOOGLE_MAPS_API_KEY")
        if not key:
            raise ValueError(
                "Falta la API key de Google. Crea una en "
                "https://console.cloud.google.com (habilita 'Geocoding API' y facturación) "
                "y pásala como api_key=... o expórtala en la variable de entorno "
                "GOOGLE_MAPS_API_KEY. Alternativa sin key: provider='nominatim'."
            )
        geolocator = GoogleV3(api_key=key, timeout=10)
        delay = min_delay if min_delay is not None else 0.05  # Google admite alta QPS
        return RateLimiter(geolocator.geocode, min_delay_seconds=delay,
                           max_retries=2, swallow_exceptions=True), _resolver_google, delay
    if provider == "nominatim":
        geolocator = Nominatim(user_agent="epsel-datathon-geocoder", timeout=10)
        delay = min_delay if min_delay is not None else 1.0  # ToS: 1 req/seg
        return RateLimiter(geolocator.geocode, min_delay_seconds=delay,
                           max_retries=2, error_wait_seconds=5.0,
                           swallow_exceptions=True), _resolver_nominatim, delay
    raise ValueError(f"provider desconocido: {provider!r} (usa 'google' o 'nominatim')")


# --------------------------------------------------------------------------- #
# API principal
# --------------------------------------------------------------------------- #
def geocode_addresses(
    direcciones: pd.Series | list[str],
    cache_path: Path,
    *,
    provider: str = "google",
    api_key: str | None = None,
    sufijo: str = SUFIJO_DEFECTO,
    min_delay: float | None = None,
    max_n: int | None = None,
    verbose: bool = True,
) -> dict[str, tuple]:
    """Geocodifica direcciones ÚNICAS -> dict {direccion: (lat, lon, precision)}.

    - `provider`: "google" (preciso, requiere key) o "nominatim" (gratis).
    - Solo consulta direcciones que no estén ya en la caché.
    - `max_n` limita cuántas direcciones NUEVAS se consultan en esta corrida.
    """
    cache_path = Path(cache_path)
    cache = _load_cache(cache_path)

    unicas = pd.Series(direcciones, dtype="object").dropna().astype(str).str.strip()
    unicas = unicas[unicas != ""].unique().tolist()
    pendientes = [d for d in unicas if d not in cache]
    if max_n is not None:
        pendientes = pendientes[:max_n]

    geocode, resolver, delay = _build_geocoder(provider, api_key, min_delay)

    if verbose:
        ya = len(unicas) - len([d for d in unicas if d not in cache])
        print(f"Proveedor: {provider} | direcciones únicas: {len(unicas):,} | "
              f"ya en caché: {ya:,} | a consultar ahora: {len(pendientes):,}")
        if pendientes:
            print(f"Tiempo estimado: ~{len(pendientes)*delay/60:.1f} min "
                  f"({delay:g} s/consulta)")

    if pendientes:
        for i, d in enumerate(pendientes, 1):
            cache[d] = resolver(geocode, d, sufijo)
            if verbose and (i % 50 == 0 or i == len(pendientes)):
                print(f"  {i}/{len(pendientes)} consultadas")
        _save_cache(cache, cache_path)

    return cache


def attach_coords(
    df: pd.DataFrame, cache: dict[str, tuple], col_dir: str = "DIRECCION",
) -> pd.DataFrame:
    """Agrega LATITUD, LONGITUD, PRECISION_COORD y COORD_VALIDA al DataFrame."""
    df = df.copy()
    df["LATITUD"] = df[col_dir].map(lambda d: cache.get(d, (None, None, None))[0])
    df["LONGITUD"] = df[col_dir].map(lambda d: cache.get(d, (None, None, None))[1])
    df["PRECISION_COORD"] = df[col_dir].map(lambda d: cache.get(d, (None, None, None))[2])
    df["COORD_VALIDA"] = [en_bbox(la, lo) for la, lo in zip(df["LATITUD"], df["LONGITUD"])]
    return df
