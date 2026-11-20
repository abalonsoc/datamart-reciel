# Data Mart comercial de Reciel

Proyecto del curso Business Intelligence and Big Data (UCV, sección A1).
Integra Nubefact, HubSpot y Google Ads en un Data Mart MySQL (esquema estrella) y lo explota en Power BI.

## Puesta en marcha (M0)

1. Instalar MySQL 8, Python 3.12 y Power BI Desktop.
2. Crear el entorno:
   ```
   python -m venv venv
   venv\Scripts\activate        # Windows  (Linux/Mac: source venv/bin/activate)
   pip install -r requirements.txt
   ```
3. Copiar `.env.example` como `.env` y completar las credenciales.
4. Poner los archivos exportados en la carpeta `datos/` (no se sube a GitHub).
5. Ejecutar `python test_conexiones.py`: debe terminar en `M0 COMPLETO`.

## Módulos
| Módulo | Carpeta / archivo |
|---|---|
| M1 Base de datos | `sql/` |
| M2–M4 Extracción | `extraccion/` |
| M5–M6 Transformación y carga | `transformacion/`, `validacion.py` |
| M7 Orquestación | `main.py` |
| M8 Dashboard | `powerbi/` |

## Seguridad
`.env` y `datos/` están en `.gitignore`. Nunca suban tokens ni datos reales de clientes.
