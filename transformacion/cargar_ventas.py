"""
M5 + M6 - Carga de dimensiones y de Hecho_Ventas desde las facturas en staging.

Lee stg_facturas y stg_facturas_items (las llena extraccion/facturas.py),
limpia y carga:
    dim_cliente   (un registro por RUC)
    dim_producto  (un registro por descripción + talla)
    hecho_ventas  (una fila por línea de factura)
Al final valida que el total cargado sea igual al de las facturas y deja el
resultado en etl_log.

Uso:
    python -m transformacion.cargar_ventas
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd
from sqlalchemy import text

import config

EQUIVALENCIAS = Path(__file__).with_name("equivalencias_categorias.csv")


# ---------- limpieza ----------
def limpiar_ruc(valor) -> str | None:
    ruc = re.sub(r"\D", "", str(valor or ""))
    return ruc if len(ruc) == 11 else None


def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def normalizar_descripcion(texto: str) -> str:
    texto = sin_tildes(str(texto)).upper()
    return re.sub(r"\s+", " ", texto).strip()


def generar_sku(descripcion: str, talla) -> str:
    """Las facturas no traen código de producto: se arma con la descripción y la talla."""
    base = re.sub(r"[^A-Z0-9]+", "-", normalizar_descripcion(descripcion)).strip("-")
    talla = str(talla).strip().upper() if pd.notna(talla) and str(talla).strip() else "UNICA"
    return f"{base}-{talla}"[:100]


def clasificar(descripcion: str, reglas: pd.DataFrame) -> tuple[str, str]:
    palabras = set(normalizar_descripcion(descripcion).split())
    for _, r in reglas.iterrows():
        if r["palabra_clave"] in palabras:
            return r["categoria"], r["tipo_proteccion"]
    return "Sin categoría", None


# ---------- carga ----------
def leer_staging(engine) -> tuple[pd.DataFrame, pd.DataFrame]:
    cab = pd.read_sql("SELECT * FROM stg_facturas", engine, dtype={"numero": str, "ruc_cliente": str, "orden_compra": str})
    det = pd.read_sql("SELECT * FROM stg_facturas_items", engine, dtype={"numero": str})
    # Al leer como texto, los vacíos llegan como "None"/"nan": se vuelven nulos de verdad
    vacios = {"None": None, "nan": None, "": None}
    cab["orden_compra"] = cab["orden_compra"].replace(vacios)
    det["talla"] = det["talla"].replace(vacios)
    return cab, det


def cargar_dim_cliente(con, cab: pd.DataFrame) -> dict:
    clientes = (cab.assign(RUC=cab["ruc_cliente"].map(limpiar_ruc))
                   .dropna(subset=["RUC"])
                   .sort_values("fecha_emision")
                   .groupby("RUC", as_index=False).last())     # la razón social más reciente
    existentes = {r[0] for r in con.execute(text("SELECT RUC FROM dim_cliente"))}
    for _, c in clientes.iterrows():
        datos = {"ruc": c["RUC"], "razon": normalizar_descripcion(c["razon_social_cliente"]), "origen": c["origen"]}
        if c["RUC"] in existentes:
            con.execute(text("UPDATE dim_cliente SET Razon_Social=:razon WHERE RUC=:ruc"), datos)
        else:
            con.execute(text("INSERT INTO dim_cliente (RUC, Razon_Social, Sector_Economico, Origen_Datos) "
                             "VALUES (:ruc, :razon, 'Sin clasificar', :origen)"), datos)
    return {r[1]: r[0] for r in con.execute(text("SELECT SK_Cliente, RUC FROM dim_cliente"))}


def cargar_dim_producto(con, det: pd.DataFrame) -> dict:
    reglas = pd.read_csv(EQUIVALENCIAS)
    productos = det.drop_duplicates(subset=["sku"])
    existentes = {r[0] for r in con.execute(text("SELECT SKU_Producto FROM dim_producto"))}
    for _, p in productos.iterrows():
        if p["sku"] in existentes:
            continue
        categoria, tipo = clasificar(p["descripcion"], reglas)
        con.execute(text("INSERT INTO dim_producto (SKU_Producto, Descripcion, Talla, Categoria, Tipo_Proteccion) "
                         "VALUES (:sku, :desc, :talla, :cat, :tipo)"),
                    {"sku": p["sku"], "desc": normalizar_descripcion(p["descripcion"]),
                     "talla": p["talla"] if pd.notna(p["talla"]) else "ÚNICA", "cat": categoria, "tipo": tipo})
    con.execute(text("UPDATE dim_producto SET Talla = 'ÚNICA' WHERE Talla IS NULL OR Talla = ''"))
    return {r[1]: r[0] for r in con.execute(text("SELECT SK_Producto, SKU_Producto FROM dim_producto"))}


def preparar_hechos(cab, det, sk_cliente, sk_producto, fechas_validas) -> pd.DataFrame:
    df = det.merge(cab, on=["serie", "numero"], how="inner", suffixes=("", "_cab"))
    df["RUC"] = df["ruc_cliente"].map(limpiar_ruc)
    df["SK_Cliente"] = df["RUC"].map(sk_cliente)
    df["SK_Producto"] = df["sku"].map(sk_producto)
    df["SK_Tiempo"] = pd.to_datetime(df["fecha_emision"]).dt.strftime("%Y%m%d").astype(int)

    # El IGV de la factura se reparte entre sus líneas según su peso en el valor de venta
    proporcion = df["valor_venta_linea"] / df["valor_venta"].where(df["valor_venta"] != 0)
    df["Monto_IGV"] = (df["igv"] * proporcion).round(2)
    df["Monto_Total_Facturado"] = (df["valor_venta_linea"] + df["Monto_IGV"]).round(2)

    descartes = df["SK_Cliente"].isna() | df["SK_Producto"].isna() | ~df["SK_Tiempo"].isin(fechas_validas)
    if descartes.any():
        print(f"[AVISO] {descartes.sum()} línea(s) descartadas (RUC inválido o fecha fuera de Dim_Tiempo)")
    no_soles = df["moneda"].str.upper() != "SOLES"
    if no_soles.any():
        print(f"[AVISO] {no_soles.sum()} línea(s) en otra moneda: se cargan sin convertir")

    df = df[~descartes]
    return pd.DataFrame({
        "SK_Cliente": df["SK_Cliente"].astype(int),
        "SK_Producto": df["SK_Producto"].astype(int),
        "SK_Tiempo": df["SK_Tiempo"],
        "SK_Vendedor": 0,          # se asigna cuando se integre HubSpot (M3)
        "SK_Campana": 0,           # se asigna cuando se integre Google Ads (M4)
        "Origen_Factura": df["origen"],
        "Serie_Factura": df["serie"],
        "Numero_Factura": df["numero"],
        "Linea_Factura": df["linea"].astype(int),
        "Numero_Orden_Compra": df["orden_compra"].where(df["orden_compra"].notna(), None),
        "Cantidad_Vendida": df["cantidad"],
        "Precio_Unitario_Sin_IGV": df["valor_unitario"],
        "Monto_Neto": df["valor_venta_linea"],
        "Monto_IGV": df["Monto_IGV"],
        "Monto_Total_Facturado": df["Monto_Total_Facturado"],
    })


def main() -> None:
    engine = config.get_engine()
    cab, det = leer_staging(engine)
    if cab.empty:
        raise SystemExit("stg_facturas está vacía: primero corre python -m extraccion.facturas")
    det["sku"] = [generar_sku(d, t) for d, t in zip(det["descripcion"], det["talla"])]

    with engine.begin() as con:
        sk_cliente = cargar_dim_cliente(con, cab)
        sk_producto = cargar_dim_producto(con, det)
        fechas_validas = {r[0] for r in con.execute(text("SELECT SK_Tiempo FROM dim_tiempo"))}
        hechos = preparar_hechos(cab, det, sk_cliente, sk_producto, fechas_validas)

        # Recarga completa: staging siempre trae todas las facturas
        con.execute(text("DELETE FROM hecho_ventas"))
        hechos.to_sql("hecho_ventas", con, if_exists="append", index=False)

        # Validación: lo cargado debe sumar lo mismo que las facturas
        total_facturas = round(cab.loc[cab["ruc_cliente"].map(limpiar_ruc).notna(), "valor_venta"].sum(), 2)
        total_cargado = round(float(con.execute(text("SELECT COALESCE(SUM(Monto_Neto),0) FROM hecho_ventas")).scalar()), 2)
        cuadra = abs(total_facturas - total_cargado) < 0.05
        con.execute(text("INSERT INTO etl_log (proceso, filas_cargadas, estado, detalle) VALUES "
                         "('M6 cargar_ventas', :n, :estado, :detalle)"),
                    {"n": len(hechos), "estado": "OK" if cuadra else "DIFERENCIA",
                     "detalle": f"Facturas S/ {total_facturas:,.2f} | Cargado S/ {total_cargado:,.2f}"})

    n_cli = len(sk_cliente)
    n_prod = len(sk_producto)
    print(f"dim_cliente: {n_cli} | dim_producto: {n_prod} | hecho_ventas: {len(hechos)} líneas")
    print(f"Validación: facturas S/ {total_facturas:,.2f} vs cargado S/ {total_cargado:,.2f} -> "
          f"{'CUADRA' if cuadra else 'NO CUADRA'}")


if __name__ == "__main__":
    main()
