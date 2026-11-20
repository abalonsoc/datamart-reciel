"""Lee la configuración desde el archivo .env."""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "dm_comercial")

HUBSPOT_TOKEN = os.getenv("HUBSPOT_TOKEN")
NUBEFACT_EXCEL = os.getenv("NUBEFACT_EXCEL")
GOOGLE_ADS_CSV = os.getenv("GOOGLE_ADS_CSV")


def get_engine(database: str | None = DB_NAME):
    """Conexión a MySQL. Con database=None se conecta al servidor sin elegir base."""
    db = f"/{database}" if database else ""
    url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}{db}?charset=utf8mb4"
    return create_engine(url)
