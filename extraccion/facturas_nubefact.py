"""
M2b - Descarga de facturas nuevas desde Nubefact.

La API de Nubefact no lista comprobantes: se consultan uno por uno por serie y
número (operación "consultar_comprobante"). Este script parte del último número
descargado de cada serie y avanza hasta que Nubefact deje de encontrar
comprobantes. Por cada factura encontrada descarga su XML a datos/facturas_xml/.

Variables en .env:
    NUBEFACT_RUTA    la RUTA de la API (https://api.nubefact.com/api/v1/...)
    NUBEFACT_TOKEN   el TOKEN de la API
    NUBEFACT_SERIES  series de factura separadas por coma, p. ej. F001
"""
import io
import json
import os
import zipfile
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

RUTA = os.getenv("NUBEFACT_RUTA")
TOKEN = os.getenv("NUBEFACT_TOKEN")
SERIES = [s.strip() for s in os.getenv("NUBEFACT_SERIES", "F001").split(",") if s.strip()]

CARPETA_XML = Path("datos/facturas_xml")
ARCHIVO_ESTADO = Path("datos/estado_nubefact.json")
FALLOS_SEGUIDOS_PARA_PARAR = 3   # tolera algún número saltado o anulado
TIPO_FACTURA = 1                  # 1 = factura en la API de Nubefact


def _cabeceras() -> dict:
    return {"Authorization": f'Token token="{TOKEN}"', "Content-Type": "application/json"}


def consultar(serie: str, numero: int) -> dict | None:
    """Devuelve la respuesta de Nubefact o None si el comprobante no existe."""
    cuerpo = {
        "operacion": "consultar_comprobante",
        "tipo_de_comprobante": TIPO_FACTURA,
        "serie": serie,
        "numero": numero,
    }
    r = requests.post(RUTA, headers=_cabeceras(), data=json.dumps(cuerpo), timeout=30)
    datos = r.json()
    if r.status_code != 200 or "errors" in datos:
        return None
    return datos


def descargar_xml(enlace: str) -> bytes:
    r = requests.get(enlace, timeout=60)
    r.raise_for_status()
    contenido = r.content
    if contenido[:2] == b"PK":  # algunos enlaces devuelven el XML comprimido
        with zipfile.ZipFile(io.BytesIO(contenido)) as z:
            nombre = next(n for n in z.namelist() if n.lower().endswith(".xml"))
            contenido = z.read(nombre)
    return contenido


def leer_estado() -> dict:
    if ARCHIVO_ESTADO.exists():
        return json.loads(ARCHIVO_ESTADO.read_text(encoding="utf-8"))
    return {}


def guardar_estado(estado: dict) -> None:
    ARCHIVO_ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVO_ESTADO.write_text(json.dumps(estado, indent=2), encoding="utf-8")


def descargar_nuevas() -> int:
    """Descarga las facturas nuevas de cada serie. Devuelve cuántas bajó."""
    if not RUTA or not TOKEN:
        print("[AVISO] Faltan NUBEFACT_RUTA o NUBEFACT_TOKEN en .env: se omite Nubefact.")
        return 0

    CARPETA_XML.mkdir(parents=True, exist_ok=True)
    estado = leer_estado()
    total = 0
    for serie in SERIES:
        numero = estado.get(serie, 0) + 1
        fallos = 0
        while fallos < FALLOS_SEGUIDOS_PARA_PARAR:
            datos = consultar(serie, numero)
            if datos is None:
                fallos += 1
            else:
                fallos = 0
                if datos.get("anulado"):
                    print(f"  {serie}-{numero}: anulada, se omite")
                elif datos.get("enlace_del_xml"):
                    xml = descargar_xml(datos["enlace_del_xml"])
                    (CARPETA_XML / f"{serie}-{numero}.xml").write_bytes(xml)
                    total += 1
                    print(f"  {serie}-{numero}: descargada")
                estado[serie] = numero   # solo avanza con comprobantes que existen
                guardar_estado(estado)
            numero += 1
    print(f"Nubefact: {total} factura(s) nueva(s)")
    return total


if __name__ == "__main__":
    descargar_nuevas()
