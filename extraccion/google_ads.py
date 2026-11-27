"""
M4 - Extracción de Google Ads.

Lee el CSV descargado de la hoja que llena el script de Google Ads
(scripts_externos/google_ads_a_sheets.js) y lo guarda en stg_google_ads.
Si el archivo no existe o no tiene filas, lo avisa y deja el staging vacío:
el resto del ETL sigue normalmente.

Uso:
    python -m extraccion.google_ads
"""
import os

import pandas as pd

import config

COLUMNAS = ["fecha", "id_cuenta", "cuenta", "id_campana", "campana", "tipo_campana", "estado",
            "costo_micros", "impresiones", "clics", "conversiones"]

# Nombres que usaba la primera versión del script (exportToSheet) -> nombres actuales
EQUIVALENCIAS = {
    "segments.date": "fecha", "campaign.id": "id_campana", "campaign.name": "campana",
    "campaign.advertising_channel_type": "tipo_campana", "campaign.status": "estado",
    "metrics.cost_micros": "costo_micros", "metrics.impressions": "impresiones",
    "metrics.clicks": "clics", "metrics.conversions": "conversiones",
}


def leer_csv(ruta: str | None) -> pd.DataFrame:
    if not ruta or not os.path.exists(ruta):
        print(f"[AVISO] No se encontró {ruta}: Google Ads queda sin datos en esta carga.")
        return pd.DataFrame(columns=COLUMNAS)
    df = pd.read_csv(ruta, dtype={"id_cuenta": str, "id_campana": str, "campaign.id": str})
    df = df.rename(columns=lambda c: EQUIVALENCIAS.get(c.strip(), c.strip()))
    for c in COLUMNAS:
        if c not in df.columns:
            df[c] = None
    df = df[COLUMNAS].dropna(subset=["fecha", "id_campana"])
    for c in ["costo_micros", "impresiones", "clics", "conversiones"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
    return df


def main() -> None:
    df = leer_csv(config.GOOGLE_ADS_CSV)
    df.to_sql("stg_google_ads", config.get_engine(), if_exists="replace", index=False)
    if df.empty:
        print("Google Ads: 0 filas (sin inversión registrada en el periodo).")
    else:
        inversion = df["costo_micros"].sum() / 1_000_000
        print(f"Google Ads: {len(df)} filas | {df['id_campana'].nunique()} campañas | "
              f"inversión S/ {inversion:,.2f} | {int(df['clics'].sum())} clics")


if __name__ == "__main__":
    main()
