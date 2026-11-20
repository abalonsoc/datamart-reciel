"""
M1 - Crea el Data Mart y llena Dim_Tiempo.

Uso (desde la carpeta del proyecto, con el venv activo):
    python -m sql.crear_datamart

Atención: vuelve a crear las tablas desde cero (borra lo que tengan).
"""
from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import text

import config

ANIO_INICIO, ANIO_FIN = 2024, 2027

# Campaña agrícola: de noviembre a abril (cruza el año). Confirmar con Reciel y ajustar.
MES_INICIO_CAMPANA, MES_FIN_CAMPANA = 11, 4

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def campana_agricola(fecha: date) -> str:
    """Nombre de la campaña agrícola de una fecha, p. ej. 'Campaña 2025-2026'."""
    if MES_INICIO_CAMPANA > MES_FIN_CAMPANA:          # cruza el año (nov-abr)
        if fecha.month >= MES_INICIO_CAMPANA:
            return f"Campaña {fecha.year}-{fecha.year + 1}"
        if fecha.month <= MES_FIN_CAMPANA:
            return f"Campaña {fecha.year - 1}-{fecha.year}"
    elif MES_INICIO_CAMPANA <= fecha.month <= MES_FIN_CAMPANA:
        return f"Campaña {fecha.year}"
    return "Fuera de campaña"


def generar_dim_tiempo() -> pd.DataFrame:
    fechas = pd.date_range(f"{ANIO_INICIO}-01-01", f"{ANIO_FIN}-12-31", freq="D")
    return pd.DataFrame({
        "SK_Tiempo": fechas.strftime("%Y%m%d").astype(int),
        "Fecha": fechas.date,
        "Anio": fechas.year,
        "Trimestre": fechas.quarter,
        "Mes": fechas.month,
        "Nombre_Mes": [MESES[m - 1] for m in fechas.month],
        "Dia": fechas.day,
        "Campana_Agricola": [campana_agricola(f) for f in fechas.date],
    })


def ejecutar_sql(ruta: Path) -> None:
    script = ruta.read_text(encoding="utf-8")
    sentencias = []
    for bloque in script.split(";"):
        lineas = [l for l in bloque.splitlines() if not l.strip().startswith("--")]
        sentencia = "\n".join(lineas).strip()
        if sentencia:
            sentencias.append(sentencia)
    with config.get_engine().begin() as con:
        for s in sentencias:
            con.execute(text(s))


def main() -> None:
    ejecutar_sql(Path(__file__).with_name("01_crear_tablas.sql"))
    print("Tablas creadas.")

    dim_tiempo = generar_dim_tiempo()
    dim_tiempo.to_sql("dim_tiempo", config.get_engine(), if_exists="append", index=False)
    print(f"Dim_Tiempo: {len(dim_tiempo)} fechas ({ANIO_INICIO}-{ANIO_FIN}).")

    with config.get_engine().connect() as con:
        tablas = [r[0] for r in con.execute(text("SHOW TABLES"))]
        con.execute(text(
            "INSERT INTO etl_log (proceso, filas_cargadas, estado, detalle) "
            "VALUES ('M1 crear_datamart', :n, 'OK', 'Tablas creadas y Dim_Tiempo cargada')"
        ), {"n": len(dim_tiempo)})
        con.commit()
    print("Tablas en dm_comercial:", ", ".join(sorted(tablas)))


if __name__ == "__main__":
    main()
