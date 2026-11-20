/**
 * Script de Google Ads (Herramientas > Acciones masivas > Secuencias de comandos).
 * Copia las métricas diarias por campaña a una hoja de Google Sheets.
 * 1. Creen una hoja vacía en Google Sheets y peguen su URL abajo.
 * 2. Para la carga inicial, cambien FECHA_INICIO a la fecha de la primera campaña.
 * 3. Luego prográmenlo "Diariamente".
 */
var URL_HOJA = 'https://docs.google.com/spreadsheets/d/1OJ38uWoe2i4XGU5VsIV7m7Xd0RJSPxQWskFDqluGZCA/edit?gid=0#gid=0';
var FECHA_INICIO = '2025-01-01';   // AAAA-MM-DD

function main() {
  var hoy = Utilities.formatDate(new Date(), AdsApp.currentAccount().getTimeZone(), 'yyyy-MM-dd');
  var consulta =
    'SELECT segments.date, campaign.id, campaign.name, ' +
    'campaign.advertising_channel_type, metrics.cost_micros, ' +
    'metrics.impressions, metrics.clicks, metrics.conversions ' +
    'FROM campaign ' +
    "WHERE segments.date BETWEEN '" + FECHA_INICIO + "' AND '" + hoy + "'";

  var hoja = SpreadsheetApp.openByUrl(URL_HOJA).getSheets()[0];
  AdsApp.report(consulta).exportToSheet(hoja);
  Logger.log('Exportado hasta ' + hoy);
}
