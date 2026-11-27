"""
M4 - Carga de Dim_Campana y Hecho_Campanas desde stg_google_ads.

  dim_campana     un registro por campaña de Google Ads (la clave 0 "Sin campaña" se conserva)
  hecho_campanas  una fila por campaña y día: inversión (S/), impresiones, clics y
                  cotizaciones generadas (conversiones registradas en Google Ads)

La inversión viene en micros (millonésimas de la moneda de la cuenta) y se divide entre 1 000 000.

Uso:
    python -m transformacion.cargar_campanas
"""
import pandas as pd
from sqlalchemy import text

import config


def main() -> None:
    engine = config.get_engine()
    with engine.begin() as con:
        try:
            stg = pd.read_sql("SELECT * FROM stg_google_ads", con, dtype={"id_campana": str})
        except Exception:
            raise SystemExit("No existe stg_google_ads: primero corre python -m extraccion.google_ads")

        # 1. dim_campana
        campanas = stg.sort_values("fecha").drop_duplicates("id_campana", keep="last")
        existentes = {r[0] for r in con.execute(text("SELECT ID_Campana_Origen FROM dim_campana"))}
        for _, c in campanas.iterrows():
            datos = {"id": c["id_campana"], "nombre": c["campana"], "tipo": c["tipo_campana"]}
            if c["id_campana"] in existentes:
                con.execute(text("UPDATE dim_campana SET Nombre_Campana=:nombre, Tipo_Estrategia=:tipo "
                                 "WHERE ID_Campana_Origen=:id"), datos)
            else:
                con.execute(text("INSERT INTO dim_campana (ID_Campana_Origen, Nombre_Campana, Plataforma, Tipo_Estrategia) "
                                 "VALUES (:id, :nombre, 'Google Ads', :tipo)"), datos)
        sk_campana = {r[1]: r[0] for r in con.execute(text("SELECT SK_Campana, ID_Campana_Origen FROM dim_campana"))}
        fechas_validas = {r[0] for r in con.execute(text("SELECT SK_Tiempo FROM dim_tiempo"))}

        # 2. hecho_campanas (recarga completa: el CSV siempre trae todo el periodo)
        con.execute(text("DELETE FROM hecho_campanas"))
        hechos = pd.DataFrame()
        if not stg.empty:
            stg["SK_Tiempo"] = pd.to_datetime(stg["fecha"]).dt.strftime("%Y%m%d").astype(int)
            stg["SK_Campana"] = stg["id_campana"].map(sk_campana)
            stg = stg[stg["SK_Tiempo"].isin(fechas_validas) & stg["SK_Campana"].notna()]
            hechos = (stg.groupby(["SK_Campana", "SK_Tiempo"], as_index=False)
                         .agg(costo=("costo_micros", "sum"), Impresiones=("impresiones", "sum"),
                              Clics=("clics", "sum"), conv=("conversiones", "sum")))
            hechos = pd.DataFrame({
                "SK_Campana": hechos["SK_Campana"].astype(int),
                "SK_Tiempo": hechos["SK_Tiempo"],
                "Inversion_Publicitaria": (hechos["costo"] / 1_000_000).round(2),
                "Impresiones": hechos["Impresiones"].astype(int),
                "Clics": hechos["Clics"].astype(int),
                "Cotizaciones_Generadas": hechos["conv"].round().astype(int),
            })
            hechos.to_sql("hecho_campanas", con, if_exists="append", index=False)

        inversion = float(hechos["Inversion_Publicitaria"].sum()) if not hechos.empty else 0.0
        detalle = f"Campañas: {len(campanas)} | Filas: {len(hechos)} | Inversión S/ {inversion:,.2f}"
        con.execute(text("INSERT INTO etl_log (proceso, filas_cargadas, estado, detalle) "
                         "VALUES ('M4 cargar_campanas', :n, 'OK', :d)"), {"n": len(hechos), "d": detalle})
    print(detalle)


if __name__ == "__main__":
    main()
