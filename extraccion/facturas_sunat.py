"""
M2 - Extracción de facturas electrónicas emitidas en el Sistema de SUNAT (SOL).

Lee un PDF de factura, extrae la cabecera y el detalle y valida que los
ítems sumen el valor de venta.

Lo usa extraccion/facturas.py, que junta estas facturas con las de Nubefact.
"""
import re
from pathlib import Path

import pandas as pd
import pdfplumber

RE_NUMERO = re.compile(r"^([EF]\d{3})-(\d+)$")
RE_FECHA = re.compile(r"Fecha de Emisi[oó]n\s*:\s*(\d{2}/\d{2}/\d{4})")
RE_RUC_CLIENTE = re.compile(r"^RUC\s*:\s*(\d{11})")
RE_MONEDA = re.compile(r"Tipo de Moneda\s*:\s*(\w+)")
RE_OBSERVACION = re.compile(r"^Observaci[oó]n\s*:\s*(.*)$")
RE_ORDEN_COMPRA = re.compile(r"Orden de Compra\s*:\s*(\S+)")
RE_ITEM = re.compile(r"^(\d[\d,]*\.\d{2})\s+(\S+)\s+(.+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})$")
RE_TALLA = re.compile(r"^TALLA\s*:\s*(\S+)", re.IGNORECASE)


def _monto(texto: str, etiqueta: str) -> float:
    m = re.search(rf"{etiqueta}\s*:\s*S/\s*([\d,]+\.\d{{2}})", texto)
    return float(m.group(1).replace(",", "")) if m else 0.0


def _num(valor: str) -> float:
    return float(valor.replace(",", ""))


def leer_factura(ruta: Path) -> tuple[dict, list[dict]]:
    """Devuelve (cabecera, items) de un PDF de factura SUNAT."""
    with pdfplumber.open(ruta) as pdf:
        texto = "\n".join(p.extract_text() or "" for p in pdf.pages)
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]

    serie = numero = ruc_cliente = observacion = None
    idx_fecha = idx_ruc = None
    for i, l in enumerate(lineas):
        if (m := RE_NUMERO.match(l)) and serie is None:
            serie, numero = m.group(1), m.group(2)
        if RE_FECHA.search(l) and idx_fecha is None:
            idx_fecha = i
        if (m := RE_RUC_CLIENTE.match(l)) and idx_fecha is not None and ruc_cliente is None:
            ruc_cliente, idx_ruc = m.group(1), i
        if (m := RE_OBSERVACION.match(l)):
            observacion = m.group(1).strip() or None

    # La razón social del cliente está entre la línea de la fecha y la del RUC;
    # el PDF a veces la parte en dos líneas alrededor de "Señor(es) :".
    partes = []
    for l in lineas[idx_fecha + 1: idx_ruc]:
        l = re.sub(r"^Señor\(es\)\s*:\s*", "", l)
        if l:
            partes.append(l)
    razon_social = " ".join(partes)

    fecha = pd.to_datetime(RE_FECHA.search(texto).group(1), format="%d/%m/%Y").date()
    moneda = RE_MONEDA.search(texto).group(1)
    oc = RE_ORDEN_COMPRA.search(texto)

    items = []
    for l in lineas:
        if (m := RE_ITEM.match(l)):
            cantidad, unidad, descripcion, valor_unit, _icbper = m.groups()
            items.append({
                "serie": serie, "numero": numero, "linea": len(items) + 1,
                "cantidad": _num(cantidad), "unidad_medida": unidad,
                "descripcion": descripcion.strip(), "talla": None,
                "valor_unitario": _num(valor_unit),
            })
        elif (m := RE_TALLA.match(l)) and items:
            items[-1]["talla"] = m.group(1)
    for it in items:
        it["valor_venta_linea"] = round(it["cantidad"] * it["valor_unitario"], 2)

    cabecera = {
        "serie": serie, "numero": numero, "fecha_emision": fecha,
        "ruc_cliente": ruc_cliente, "razon_social_cliente": razon_social,
        "moneda": moneda, "orden_compra": oc.group(1) if oc else None,
        "observacion": observacion,
        "valor_venta": _monto(texto, "Valor Venta"),
        "igv": _monto(texto, "IGV"),
        "importe_total": _monto(texto, "Importe Total"),
        "archivo": ruta.name,
    }
    suma_items = round(sum(i["valor_venta_linea"] for i in items), 2)
    cabecera["cuadra"] = abs(suma_items - cabecera["valor_venta"]) < 0.05
    return cabecera, items


if __name__ == "__main__":
    from extraccion.facturas import main
    main()
