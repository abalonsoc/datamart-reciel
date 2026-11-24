"""
M3 - Extracción de HubSpot.

Baja, con el token de la Private App (solo lectura):
    stg_hubspot_empresas  empresas: nombre, RUC, sector (industria) y propietario
    stg_hubspot_deals     negocios: monto, fecha de cierre, etapa, si está ganado,
                          vendedor y empresa asociada
    stg_hubspot_owners    usuarios propietarios (vendedores)

El RUC suele ser una propiedad personalizada de la empresa. El script la busca
sola (una propiedad cuyo nombre o etiqueta contenga "RUC"); si tiene otro
nombre, pónganlo en .env como HUBSPOT_PROP_RUC.

Uso:
    python -m extraccion.hubspot
"""
import os
import re

import pandas as pd
import requests

import config

BASE = "https://api.hubapi.com"


def _get(ruta: str, params: dict | None = None) -> dict:
    r = requests.get(f"{BASE}{ruta}", params=params or {}, timeout=60,
                     headers={"Authorization": f"Bearer {config.HUBSPOT_TOKEN}"})
    r.raise_for_status()
    return r.json()


def _paginar(ruta: str, params: dict) -> list[dict]:
    resultados, despues = [], None
    while True:
        p = dict(params, limit=100)
        if despues:
            p["after"] = despues
        datos = _get(ruta, p)
        resultados.extend(datos.get("results", []))
        despues = datos.get("paging", {}).get("next", {}).get("after")
        if not despues:
            return resultados


def propiedades_empresa() -> tuple[str | None, dict]:
    """Devuelve (nombre interno de la propiedad RUC, {valor de industria: etiqueta})."""
    props = _get("/crm/v3/properties/companies").get("results", [])
    prop_ruc = os.getenv("HUBSPOT_PROP_RUC")
    if not prop_ruc:
        candidatas = [p["name"] for p in props
                      if re.search(r"\bruc\b", p["name"], re.I) or re.search(r"\bRUC\b", p.get("label", ""))]
        prop_ruc = candidatas[0] if candidatas else None
    industria = next((p for p in props if p["name"] == "industry"), {})
    etiquetas = {o["value"]: o["label"] for o in industria.get("options", [])}
    return prop_ruc, etiquetas


def extraer_empresas() -> pd.DataFrame:
    prop_ruc, etiquetas = propiedades_empresa()
    campos = ["name", "industry", "hubspot_owner_id"] + ([prop_ruc] if prop_ruc else [])
    filas = []
    for e in _paginar("/crm/v3/objects/companies", {"properties": ",".join(campos)}):
        p = e.get("properties", {})
        filas.append({
            "id_empresa": e["id"],
            "nombre": p.get("name"),
            "ruc": re.sub(r"\D", "", p.get(prop_ruc) or "") or None if prop_ruc else None,
            "industria": etiquetas.get(p.get("industry"), p.get("industry")),
            "id_owner": p.get("hubspot_owner_id"),
        })
    if not prop_ruc:
        print("[AVISO] No se encontró una propiedad de RUC en las empresas de HubSpot: "
              "se cruzará por razón social. Si existe con otro nombre, pónganlo en HUBSPOT_PROP_RUC.")
    return pd.DataFrame(filas, columns=["id_empresa", "nombre", "ruc", "industria", "id_owner"])


def etapas_ganadas() -> set[str]:
    """Etapas de negocio con probabilidad 1.0 (cerrado ganado) en todos los pipelines."""
    ganadas = set()
    for pipeline in _get("/crm/v3/pipelines/deals").get("results", []):
        for etapa in pipeline.get("stages", []):
            if str(etapa.get("metadata", {}).get("probability")) in ("1.0", "1"):
                ganadas.add(etapa["id"])
    return ganadas


def extraer_deals() -> pd.DataFrame:
    ganadas = etapas_ganadas()
    params = {"properties": "dealname,amount,closedate,dealstage,hubspot_owner_id",
              "associations": "companies"}
    filas = []
    for d in _paginar("/crm/v3/objects/deals", params):
        p = d.get("properties", {})
        empresas = d.get("associations", {}).get("companies", {}).get("results", [])
        filas.append({
            "id_deal": d["id"],
            "nombre": p.get("dealname"),
            "monto": float(p["amount"]) if p.get("amount") else None,
            "fecha_cierre": pd.to_datetime(p.get("closedate"), utc=True).date() if p.get("closedate") else None,
            "etapa": p.get("dealstage"),
            "ganado": p.get("dealstage") in ganadas,
            "id_owner": p.get("hubspot_owner_id"),
            "id_empresa": empresas[0]["id"] if empresas else None,
        })
    return pd.DataFrame(filas, columns=["id_deal", "nombre", "monto", "fecha_cierre", "etapa",
                                        "ganado", "id_owner", "id_empresa"])


def extraer_owners() -> pd.DataFrame:
    filas = [{
        "id_owner": str(o["id"]),
        "nombre": " ".join(x for x in [o.get("firstName"), o.get("lastName")] if x) or o.get("email"),
        "email": o.get("email"),
    } for o in _paginar("/crm/v3/owners", {})]
    return pd.DataFrame(filas, columns=["id_owner", "nombre", "email"])


def main() -> None:
    if not config.HUBSPOT_TOKEN:
        raise SystemExit("Falta HUBSPOT_TOKEN en .env")
    empresas, deals, owners = extraer_empresas(), extraer_deals(), extraer_owners()
    engine = config.get_engine()
    empresas.to_sql("stg_hubspot_empresas", engine, if_exists="replace", index=False)
    deals.to_sql("stg_hubspot_deals", engine, if_exists="replace", index=False)
    owners.to_sql("stg_hubspot_owners", engine, if_exists="replace", index=False)
    con_ruc = empresas["ruc"].notna().sum()
    print(f"HubSpot: {len(empresas)} empresas ({con_ruc} con RUC) | {len(deals)} deals "
          f"({int(deals['ganado'].sum()) if not deals.empty else 0} ganados) | {len(owners)} vendedores")


if __name__ == "__main__":
    main()
