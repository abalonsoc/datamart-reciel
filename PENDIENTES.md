# Pendientes del proyecto Data Mart Reciel

Última actualización: 27/11/2026 (informe corregido)

## Data Mart (implementación)

| Módulo | Estado | Qué falta |
|---|---|---|
| M0 Entorno y accesos | Hecho | Solo Google Ads (ver M4) |
| M1 Base de datos | Hecho | — (`Nombre_Comercial` agregado a `dim_cliente` el 27/11) |
| M2 Facturas (SUNAT PDF + Nubefact API) | Hecho | Cargar más facturas (ver abajo) |
| M3 HubSpot | Código listo | En HubSpot: completar el Sector de las empresas y crear Estudio Grau (RUC 20101093027) con su negocio `Factura E001-509` |
| M4 Google Ads | Pendiente | Autorizar el script en incógnito, CSV, extractor de `hecho_campanas`, ROAS y atribución |
| M5–M6 Dimensiones y hecho_ventas | Hecho | — |
| M7 Carga automática diaria | Código listo | Programar la tarea en Windows con `ejecutar_etl.bat` y tomar capturas |
| M8 Dashboard | Hecho | Páginas Resumen, Clientes y Productos listas. Falta: guardar el archivo en `powerbi/dashboard_reciel.pbix`. La página Marketing se agrega con M4/M9. Sin análisis por vendedor (un solo encargado de ventas) |
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
- [x] Coherencia del informe con lo implementado (27/11/2026): fuentes SUNAT SOL + Nubefact, KPIs por factura, fases 1 y 2 en 1.7, modelo 2.3.5/2.4, ETL 2.5 en pasado, numeración.
- [ ] Actualizar el diagrama del esquema estrella en dbdiagram (`Talla`, `Dia`, `Origen_Factura`, `Linea_Factura`).
- [ ] No mencionar en el informe que HubSpot no se usaba antes del proyecto.

### Formato
- [ ] Insertar las 5 figuras (antecedentes, silos, Hefesto, modelo conceptual, ETL) y capturas del dashboard, con "Figura N", título y fuente.
- [ ] Numerar las tablas como "Tabla N".
- [ ] Corregir numeración: "III. 2.5.1" → "2.5.1"; "IV. CONCLUSIONES" → "III. CONCLUSIONES".
- [ ] Quitar textos de guía de los títulos (2.4, 2.5.2).
- [ ] 2.2.1 tiene 7 preguntas y el acta 8: alinear.
- [ ] Agregar Bernabeu (2010), Hefesto, a las referencias en ISO 690.
- [ ] Anexos: GitHub, `etl_log`, tarea programada y dashboard.
