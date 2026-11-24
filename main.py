"""
M7 - Orquestación del ETL del Data Mart comercial de Reciel.

Ejecuta todo el proceso en orden:
    1. Extracción de facturas (Nubefact por API + PDF de SUNAT) -> staging
    2. Extracción de HubSpot (empresas, deals, vendedores) -> staging
    3. Carga de dimensiones y hecho_ventas (incluye la validación contra las facturas)
    4. Sector del cliente y vendedor de cada venta desde HubSpot

Si un paso falla, se detiene, deja el error en etl_log y en datos/logs/,
y termina con código 1 para que el Programador de tareas lo marque como fallido.

Uso:
    python main.py                 # proceso completo
    python main.py --sin-nubefact  # sin consultar la API de Nubefact
"""
import logging
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

import config

CARPETA_LOGS = Path("datos/logs")


def configurar_log() -> logging.Logger:
    CARPETA_LOGS.mkdir(parents=True, exist_ok=True)
    archivo = CARPETA_LOGS / f"etl_{datetime.now():%Y%m%d}.log"
    log = logging.getLogger("etl")
    log.setLevel(logging.INFO)
    log.handlers.clear()   # evita líneas duplicadas si main() se llama más de una vez
    formato = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")
    for destino in (logging.FileHandler(archivo, encoding="utf-8"), logging.StreamHandler(sys.stdout)):
        destino.setFormatter(formato)
        log.addHandler(destino)
    return log


def registrar_en_bd(proceso: str, estado: str, detalle: str) -> None:
    """Deja constancia en etl_log; si la base no responde, no interrumpe el registro en archivo."""
    try:
        with config.get_engine().begin() as con:
            con.execute(text("INSERT INTO etl_log (proceso, filas_cargadas, estado, detalle) "
                             "VALUES (:p, NULL, :e, :d)"), {"p": proceso, "e": estado, "d": detalle[:2000]})
    except Exception:
        pass


def paso_extraer_facturas() -> None:
    from extraccion import facturas
    facturas.main()


def paso_cargar_ventas() -> None:
    from transformacion import cargar_ventas
    cargar_ventas.main()


def paso_extraer_hubspot() -> None:
    from extraccion import hubspot
    hubspot.main()


def paso_enriquecer_hubspot() -> None:
    from transformacion import enriquecer_hubspot
    enriquecer_hubspot.main()


# (nombre, función, crítico). Si un paso no crítico falla, se avisa y el ETL continúa.
PASOS = [
    ("Extracción de facturas", paso_extraer_facturas, True),
    ("Extracción de HubSpot", paso_extraer_hubspot, False),
    ("Carga de dimensiones y hecho_ventas", paso_cargar_ventas, True),
    ("Sector y vendedor desde HubSpot", paso_enriquecer_hubspot, False),
]


def main() -> int:
    log = configurar_log()
    inicio = time.time()
    log.info("=== Inicio del ETL ===")

    avisos = 0
    for nombre, funcion, critico in PASOS:
        t0 = time.time()
        log.info(f"-> {nombre}")
        error = None
        try:
            funcion()
        except SystemExit as e:          # los módulos usan sys.exit para errores esperados
            if e.code not in (None, 0):
                error = str(e.code)
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            log.debug(traceback.format_exc())
            if critico:
                log.error(traceback.format_exc())

        if error is None:
            log.info(f"   OK ({time.time() - t0:.1f} s)")
        elif critico:
            log.error(f"{nombre}: {error}")
            registrar_en_bd(f"M7 {nombre}", "ERROR", error)
            return 1
        else:
            avisos += 1
            log.warning(f"{nombre} (no crítico, se continúa): {error}")
            registrar_en_bd(f"M7 {nombre}", "AVISO", error)

    duracion = time.time() - inicio
    estado = "OK" if avisos == 0 else "OK CON AVISOS"
    log.info(f"=== ETL terminado ({estado}) en {duracion:.1f} s ===")
    registrar_en_bd("M7 ETL completo", estado, f"Duración {duracion:.1f} s | avisos: {avisos}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
