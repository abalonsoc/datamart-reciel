"""
Lector de facturas electrónicas en formato XML UBL 2.1 (estándar SUNAT).

Lo usan las facturas que llegan de Nubefact (y sirve para cualquier XML
descargado de SUNAT). Devuelve la misma estructura que el lector de PDF,
para que todas las facturas terminen en las mismas tablas de staging.
"""
import re
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}
RE_TALLA = re.compile(r"\bTALLA\s*:?\s*(\S+)\s*$", re.IGNORECASE)
MONEDAS = {"PEN": "SOLES", "USD": "DOLARES"}


def _txt(nodo, ruta: str, defecto=None):
    el = nodo.find(ruta, NS)
    return el.text.strip() if el is not None and el.text else defecto


def _num(nodo, ruta: str) -> float:
    valor = _txt(nodo, ruta)
    return float(valor) if valor else 0.0


def leer_xml(contenido: bytes, archivo: str = "") -> tuple[dict, list[dict]]:
    raiz = ET.fromstring(contenido)
    serie, numero = _txt(raiz, "cbc:ID").split("-")
    cliente = raiz.find("cac:AccountingCustomerParty/cac:Party", NS)

    items = []
    for linea in raiz.findall("cac:InvoiceLine", NS):
        descripcion = " ".join(
            d.text.strip() for d in linea.findall("cac:Item/cbc:Description", NS) if d.text
        )
        talla = None
        if (m := RE_TALLA.search(descripcion)):
            talla = m.group(1)
            descripcion = descripcion[: m.start()].strip()
        cantidad_el = linea.find("cbc:InvoicedQuantity", NS)
        items.append({
            "serie": serie, "numero": str(int(numero)), "linea": len(items) + 1,
            "cantidad": float(cantidad_el.text),
            "unidad_medida": "UNIDAD" if cantidad_el.get("unitCode") == "NIU" else cantidad_el.get("unitCode"),
            "descripcion": descripcion, "talla": talla,
            "valor_unitario": _num(linea, "cac:Price/cbc:PriceAmount"),
            "valor_venta_linea": _num(linea, "cbc:LineExtensionAmount"),
        })

    moneda = _txt(raiz, "cbc:DocumentCurrencyCode")
    cabecera = {
        "serie": serie, "numero": str(int(numero)),
        "fecha_emision": date.fromisoformat(_txt(raiz, "cbc:IssueDate")),
        "ruc_cliente": _txt(cliente, "cac:PartyIdentification/cbc:ID"),
        "razon_social_cliente": _txt(cliente, "cac:PartyLegalEntity/cbc:RegistrationName"),
        "moneda": MONEDAS.get(moneda, moneda),
        "orden_compra": _txt(raiz, "cac:OrderReference/cbc:ID"),
        "observacion": _txt(raiz, "cbc:Note"),
        "valor_venta": _num(raiz, "cac:LegalMonetaryTotal/cbc:LineExtensionAmount"),
        "igv": _num(raiz, "cac:TaxTotal/cbc:TaxAmount"),
        "importe_total": _num(raiz, "cac:LegalMonetaryTotal/cbc:PayableAmount"),
        "archivo": archivo,
    }
    suma = round(sum(i["valor_venta_linea"] for i in items), 2)
    cabecera["cuadra"] = abs(suma - cabecera["valor_venta"]) < 0.05
    return cabecera, items


def leer_archivo(ruta: Path) -> tuple[dict, list[dict]]:
    return leer_xml(ruta.read_bytes(), ruta.name)
