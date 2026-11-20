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

# 3. Facturas SUNAT en PDF
from pathlib import Path
pdfs = list(Path("datos/facturas_pdf").glob("*.pdf"))
resultado("Facturas SUNAT (PDF)", len(pdfs) > 0, f"({len(pdfs)} archivos en datos/facturas_pdf)")

# 4. API de Nubefact (consulta el comprobante 1 de la serie solo para probar el acceso)
if not (config.NUBEFACT_RUTA and config.NUBEFACT_TOKEN):
    resultado("Nubefact API", False, "-> faltan NUBEFACT_RUTA o NUBEFACT_TOKEN en .env")
else:
    import json as _json
    serie = config.NUBEFACT_SERIES.split(",")[0].strip()
    r = requests.post(
        config.NUBEFACT_RUTA,
        headers={"Authorization": f'Token token="{config.NUBEFACT_TOKEN}"', "Content-Type": "application/json"},
        data=_json.dumps({"operacion": "consultar_comprobante", "tipo_de_comprobante": 1, "serie": serie, "numero": 1}),
        timeout=30,
    )
    datos = r.json()
    # Si responde que el documento no existe, el acceso igual funciona (aún no hay facturas).
    acceso_ok = r.status_code == 200 or "no existe" in str(datos.get("errors", "")).lower()
    resultado("Nubefact API", acceso_ok, f"(HTTP {r.status_code}: {datos.get('errors', 'OK')})")

# 5. CSV de Google Ads (opcional por ahora: solo alimenta Hecho_Campanas y el ROAS)
ruta = config.GOOGLE_ADS_CSV
if ruta and os.path.exists(ruta):
    df = pd.read_csv(ruta)
    print(f"[OK ] CSV Google Ads ({len(df)} filas)")
else:
    print(f"[PENDIENTE] CSV Google Ads -> se hará después ({ruta})")

print("\nM0 COMPLETO" if ok else "\nFaltan puntos por resolver")
