"""
M3 - Enriquece el Data Mart con los datos de HubSpot.

Debe correr DESPUÉS de cargar_ventas (que recarga hecho_ventas con el vendedor en 0):
    1. dim_vendedor: un registro por usuario propietario de HubSpot.
    2. dim_cliente: completa el sector económico (industria de la empresa en HubSpot).
    3. hecho_ventas: asigna el vendedor de cada factura. Usa el dueño del negocio
       ganado de esa empresa con fecha de cierre más cercana (hasta 90 días antes o
       después de la factura); si no hay negocio, el dueño de la empresa.

El cliente se cruza por RUC; si la empresa de HubSpot no tiene RUC, por razón social.

Uso:
    python -m transformacion.enriquecer_hubspot
"""
import re

import pandas as pd
from sqlalchemy import text

import config

VENTANA_DIAS = 90
FORMAS_SOCIETARIAS = r"\b(S\.?\s?A\.?\s?C\.?|S\.?\s?A\.?\s?A\.?|S\.?\s?A\.?|S\.?\s?R\.?\s?L\.?|E\.?\s?I\.?\s?R\.?\s?L\.?|SUCURSAL DEL PERU|LIMITADA|LTDA\.?)\b"


def nombre_clave(nombre) -> str:
    """Razón social sin forma societaria ni signos, para cruzar por nombre."""
    import unicodedata
    t = "".join(c for c in unicodedata.normalize("NFD", str(nombre or "")) if unicodedata.category(c) != "Mn").upper()
    t = re.sub(FORMAS_SOCIETARIAS, " ", t)
    return re.sub(r"[^A-Z0-9]+", " ", t).strip()


def tabla_existe(con, nombre: str) -> bool:
    try:
        con.execute(text(f"SELECT 1 FROM {nombre} LIMIT 1"))
        return True
    except Exception:
        return False


def main() -> None:
    engine = config.get_engine()
    with engine.begin() as con:
        if not tabla_existe(con, "stg_hubspot_empresas"):
            raise SystemExit("No hay datos de HubSpot: primero corre python -m extraccion.hubspot")

        empresas = pd.read_sql("SELECT * FROM stg_hubspot_empresas", con, dtype={"id_empresa": str, "ruc": str, "id_owner": str})
        deals = pd.read_sql("SELECT * FROM stg_hubspot_deals", con, dtype={"id_empresa": str, "id_owner": str})
        owners = pd.read_sql("SELECT * FROM stg_hubspot_owners", con, dtype={"id_owner": str})

        # 1. dim_vendedor
        existentes = {r[0] for r in con.execute(text("SELECT ID_HubSpot_Owner FROM dim_vendedor"))}
        for _, o in owners.iterrows():
            datos = {"id": o["id_owner"], "nombre": o["nombre"], "email": o["email"]}
            if o["id_owner"] in existentes:
                con.execute(text("UPDATE dim_vendedor SET Nombre_Completo=:nombre, Email=:email "
                                 "WHERE ID_HubSpot_Owner=:id"), datos)
            else:
                con.execute(text("INSERT INTO dim_vendedor (ID_HubSpot_Owner, Nombre_Completo, Email) "
                                 "VALUES (:id, :nombre, :email)"), datos)
        sk_vendedor = {r[1]: r[0] for r in con.execute(text("SELECT SK_Vendedor, ID_HubSpot_Owner FROM dim_vendedor"))}

        # 2. Cruce cliente del Data Mart <-> empresa de HubSpot
        clientes = pd.read_sql("SELECT SK_Cliente, RUC, Razon_Social FROM dim_cliente", con, dtype={"RUC": str})
        por_ruc = empresas.dropna(subset=["ruc"]).drop_duplicates("ruc").set_index("ruc")["id_empresa"]
        empresas["clave"] = empresas["nombre"].map(nombre_clave)
        por_nombre = empresas.drop_duplicates("clave").set_index("clave")["id_empresa"]
        clientes["id_empresa"] = clientes["RUC"].map(por_ruc)
        sin_ruc = clientes["id_empresa"].isna()
        clientes.loc[sin_ruc, "id_empresa"] = clientes.loc[sin_ruc, "Razon_Social"].map(nombre_clave).map(por_nombre)

        info_empresa = empresas.set_index("id_empresa")
        for _, c in clientes.dropna(subset=["id_empresa"]).iterrows():
            sector = info_empresa.at[c["id_empresa"], "industria"]
            if pd.notna(sector) and sector:
                con.execute(text("UPDATE dim_cliente SET Sector_Economico=:s WHERE SK_Cliente=:k"),
                            {"s": sector, "k": int(c["SK_Cliente"])})

        # 3. Vendedor de cada factura
        facturas = pd.read_sql(
            "SELECT DISTINCT h.Serie_Factura, h.Numero_Factura, h.SK_Cliente, t.Fecha "
            "FROM hecho_ventas h JOIN dim_tiempo t ON t.SK_Tiempo = h.SK_Tiempo", con)
        facturas = facturas.merge(clientes[["SK_Cliente", "id_empresa"]], on="SK_Cliente", how="left")
        facturas["Fecha"] = pd.to_datetime(facturas["Fecha"])
        ganados = deals[deals["ganado"].astype(bool) & deals["id_owner"].notna()].copy()
        ganados["fecha_cierre"] = pd.to_datetime(ganados["fecha_cierre"])

        asignadas = 0
        for _, f in facturas.iterrows():
            owner = None
            if pd.notna(f["id_empresa"]):
                candidatos = ganados[ganados["id_empresa"] == f["id_empresa"]].copy()
                if not candidatos.empty:
                    candidatos["dias"] = (candidatos["fecha_cierre"] - f["Fecha"]).abs().dt.days
                    candidatos = candidatos[candidatos["dias"] <= VENTANA_DIAS]
                    if not candidatos.empty:
                        owner = candidatos.sort_values("dias").iloc[0]["id_owner"]
                if owner is None:
                    owner = info_empresa.at[f["id_empresa"], "id_owner"]
            sk = sk_vendedor.get(owner, 0) if pd.notna(owner) else 0
            if sk:
                asignadas += 1
            con.execute(text("UPDATE hecho_ventas SET SK_Vendedor=:sk "
                             "WHERE Serie_Factura=:s AND Numero_Factura=:n"),
                        {"sk": sk, "s": f["Serie_Factura"], "n": f["Numero_Factura"]})

        cruzados = clientes["id_empresa"].notna().sum()
        detalle = (f"Clientes cruzados con HubSpot: {cruzados}/{len(clientes)} | "
                   f"Facturas con vendedor: {asignadas}/{len(facturas)} | Vendedores: {len(owners)}")
        con.execute(text("INSERT INTO etl_log (proceso, filas_cargadas, estado, detalle) "
                         "VALUES ('M3 enriquecer_hubspot', :n, 'OK', :d)"), {"n": asignadas, "d": detalle})
    print(detalle)
    sin_cruce = clientes[clientes["id_empresa"].isna()]["Razon_Social"].tolist()
    if sin_cruce:
        print("[AVISO] Clientes sin empresa en HubSpot (revisa que existan y tengan RUC):")
        for n in sin_cruce:
            print("   -", n)


if __name__ == "__main__":
    main()
