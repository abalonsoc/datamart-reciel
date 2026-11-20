"""Verifica que el entorno del M0 está listo. Ejecutar: python test_conexiones.py"""
import os
import requests
import pandas as pd
from sqlalchemy import text
import config

ok = True

def resultado(nombre, exito, detalle=""):
    global ok
    ok = ok and exito
    print(f"[{'OK ' if exito else 'ERROR'}] {nombre} {detalle}")

# 1. MySQL
try:
    with config.get_engine(database=None).connect() as con:
        version = con.execute(text("SELECT VERSION()")).scalar()
    resultado("MySQL", True, f"(versión {version})")
except Exception as e:
    resultado("MySQL", False, f"-> {e}")

# 2. HubSpot
if not config.HUBSPOT_TOKEN:
    resultado("HubSpot", False, "-> falta HUBSPOT_TOKEN en .env")
else:
    r = requests.get(
        "https://api.hubapi.com/crm/v3/objects/companies",
        headers={"Authorization": f"Bearer {config.HUBSPOT_TOKEN}"},
        params={"limit": 1},
        timeout=30,
    )
    resultado("HubSpot", r.status_code == 200, f"(HTTP {r.status_code})")

# 3. Excel de Nubefact
ruta = config.NUBEFACT_EXCEL
if ruta and os.path.exists(ruta):
    df = pd.read_excel(ruta)
    resultado("Excel Nubefact", True, f"({len(df)} filas; columnas: {list(df.columns)[:6]}...)")
else:
    resultado("Excel Nubefact", False, f"-> no se encontró {ruta}")

# 4. CSV de Google Ads
ruta = config.GOOGLE_ADS_CSV
if ruta and os.path.exists(ruta):
    df = pd.read_csv(ruta)
    resultado("CSV Google Ads", True, f"({len(df)} filas)")
else:
    resultado("CSV Google Ads", False, f"-> no se encontró {ruta}")

print("\nM0 COMPLETO" if ok else "\nFaltan puntos por resolver")
