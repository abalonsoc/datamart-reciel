"""
M2 - Extracción unificada de facturas.

Junta en las mismas tablas de staging (stg_facturas y stg_facturas_items):
  * las facturas en PDF emitidas en el Sistema de SUNAT (datos/facturas_pdf/)
  * las facturas en XML descargadas de Nubefact          (datos/facturas_xml/)

Uso:
    python -m extraccion.facturas              # descarga de Nubefact + carga en MySQL
    python -m extraccion.facturas --sin-nubefact
    python -m extraccion.facturas --solo-csv   # no carga en MySQL
"""
import sys
from pathlib import Path

import pandas as pd

from extraccion import facturas_sunat, ubl_xml

CARPETA_PDF = Path("datos/facturas_pdf")
CARPETA_XML = Path("datos/facturas_xml")
CARPETA_SALIDA = Path("datos/staging")


def extraer() -> tuple[pd.DataFrame, pd.DataFrame]:
    cabeceras, detalle = [], []
    fuentes = [(CARPETA_PDF, "*.pdf", facturas_sunat.leer_factura, "SUNAT_SOL"),
               (CARPETA_XML, "*.xml", ubl_xml.leer_archivo, "NUBEFACT")]
    for carpeta, patron, lector, origen in fuentes:
        for ruta in sorted(carpeta.glob(patron)):
            try:
                cab, items = lector(ruta)
                cab["origen"] = origen
                cabeceras.append(cab)
                detalle.extend(items)
            except Exception as e:  # una factura mal leída no detiene las demás
                print(f"[ERROR] {ruta.name}: {e}")
    df_cab = pd.DataFrame(cabeceras)
    df_det = pd.DataFrame(detalle)
    if not df_cab.empty:
        df_cab = df_cab.drop_duplicates(subset=["serie", "numero"])
        df_det = df_det.drop_duplicates(subset=["serie", "numero", "linea"])
    return df_cab, df_det


def cargar_staging(df_cab: pd.DataFrame, df_det: pd.DataFrame) -> None:
    import config
    engine = config.get_engine()
    df_cab.to_sql("stg_facturas", engine, if_exists="replace", index=False)
    df_det.to_sql("stg_facturas_items", engine, if_exists="replace", index=False)


def main() -> None:
    if "--sin-nubefact" not in sys.argv:
        from extraccion import facturas_nubefact
        facturas_nubefact.descargar_nuevas()

    df_cab, df_det = extraer()
    if df_cab.empty:
        sys.exit("No hay facturas en datos/facturas_pdf/ ni en datos/facturas_xml/")

    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    df_cab.to_csv(CARPETA_SALIDA / "stg_facturas.csv", index=False, encoding="utf-8-sig")
    df_det.to_csv(CARPETA_SALIDA / "stg_facturas_items.csv", index=False, encoding="utf-8-sig")

    print(f"\nFacturas: {len(df_cab)} | Ítems: {len(df_det)}")
    print(df_cab[["origen", "serie", "numero", "fecha_emision", "ruc_cliente",
                  "valor_venta", "cuadra"]].to_string(index=False))
    if not df_cab["cuadra"].all():
        print("[AVISO] Hay facturas cuyos ítems no suman el valor de venta: revísalas.")

    if "--solo-csv" not in sys.argv:
        cargar_staging(df_cab, df_det)
        print("Cargado en MySQL: stg_facturas y stg_facturas_items")


if __name__ == "__main__":
    main()
