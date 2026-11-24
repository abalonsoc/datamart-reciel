# Pendientes del proyecto Data Mart Reciel

Última actualización: 24/11/2026

## Data Mart (implementación)

| Módulo | Estado | Qué falta |
|---|---|---|
| M0 Entorno y accesos | Hecho | Solo Google Ads (ver M4) |
| M1 Base de datos | Hecho | — |
| M2 Facturas (SUNAT PDF + Nubefact API) | Hecho | Cargar más facturas (ver abajo) |
| M3 HubSpot | En curso | Sector de clientes, vendedores y vendedor por venta |
| M4 Google Ads | Pendiente | Autorizar el script en incógnito, CSV, extractor de `hecho_campanas`, ROAS y atribución |
| M5–M6 Dimensiones y hecho_ventas | Hecho | — |
| M7 Carga automática diaria | Hecho | Programar la tarea en Windows y tomar capturas |
| M8 Dashboard | Primera versión | Formato S/ y %, unidades "Ninguno", filtros, 4 páginas, guardar `powerbi/dashboard_reciel.pbix` |
| M9 Cotizaciones web y OC | Pendiente | Extraer `leads`/`lead_items` del MySQL web y la hoja de OC; tasa de conversión y embudo |

### Datos
- [ ] Cargar más facturas de SUNAT SOL (mínimo razonable: 20–30 facturas, 6+ meses, ~10 clientes; ideal: últimos 12 meses).
- [ ] Confirmar con Reciel los meses de la campaña agrícola (hoy: noviembre a abril).
- [ ] Confirmar la serie de facturas en Nubefact cuando emitan la primera.
- [ ] Confirmar qué es el "001-2211" de la observación de las facturas (¿número de OC o de guía?).

## Informe

### Contenido que falta
- [ ] Sección 2.6 "Implementación y resultados": herramientas, script SQL, modelo en Power BI, extracción, validación (`etl_log`), carga diaria y capturas del dashboard.
- [ ] Conclusiones: una por objetivo específico, con números reales.
- [ ] ODS 8 (metas 8.2 y 8.8): la guía lo exige.

### Actualizaciones por la implementación
- [ ] Cambiar "Nubefact" por "SUNAT SOL (ventas históricas) y Nubefact (ventas nuevas)" en introducción, 1.6, 1.8, 2.3.1, 2.3.3, 2.4.2 y 2.5.
- [ ] Diagrama del esquema estrella (2.4): agregar `Talla`, `Dia`, `Origen_Factura`, `Linea_Factura`.
- [ ] Ticket promedio por factura, no por OC (1.5 y pregunta 3).
- [ ] Alcance (1.7): ventas implementadas; Google Ads, cotizaciones y OC en segunda fase.
- [ ] Pasar la sección 2.5 de futuro a pasado.

### Formato
- [ ] Insertar las 5 figuras (antecedentes, silos, Hefesto, modelo conceptual, ETL) y capturas del dashboard, con "Figura N", título y fuente.
- [ ] Numerar las tablas como "Tabla N".
- [ ] Corregir numeración: "III. 2.5.1" → "2.5.1"; "IV. CONCLUSIONES" → "III. CONCLUSIONES".
- [ ] Quitar textos de guía de los títulos (2.4, 2.5.2).
- [ ] 2.2.1 tiene 7 preguntas y el acta 8: alinear.
- [ ] Agregar Bernabeu (2010), Hefesto, a las referencias en ISO 690.
- [ ] Anexos: GitHub, `etl_log`, tarea programada y dashboard.
