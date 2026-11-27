/**
 * Script de Google Ads (Herramientas > Acciones masivas > Secuencias de comandos).
 * Copia las métricas diarias por campaña a una hoja de Google Sheets.
 *
 * Funciona en una cuenta normal y también en una cuenta de administrador (MCC):
 * en ese caso recorre cada cuenta de cliente y junta sus campañas.
 *
 * 1. Crea una hoja vacía en Google Sheets (con la misma cuenta de Google) y pega su URL abajo.
 * 2. En FECHA_INICIO pon una fecha anterior a la primera campaña.
 * 3. Ejecuta y revisa la pestaña "Registros": muestra cada cuenta y cuántas filas aportó.
 * 4. Luego prográmalo "Diariamente".
 */
var URL_HOJA = 'https://docs.google.com/spreadsheets/d/1OJ38uWoe2i4XGU5VsIV7m7Xd0RJSPxQWskFDqluGZCA/edit';
var FECHA_INICIO = '2025-01-01';   // AAAA-MM-DD

var COLUMNAS = ['fecha', 'id_cuenta', 'cuenta', 'id_campana', 'campana', 'tipo_campana', 'estado',
                'costo_micros', 'impresiones', 'clics', 'conversiones'];

function main() {
  var filas = [COLUMNAS];
  var esAdministrador = (typeof AdsManagerApp !== 'undefined');

  if (esAdministrador) {
    Logger.log('Cuenta de administrador: se recorren sus cuentas de cliente');
    var cuentas = AdsManagerApp.accounts().get();
    Logger.log('Cuentas de cliente encontradas: ' + cuentas.totalNumEntities());
    while (cuentas.hasNext()) {
      var cuenta = cuentas.next();
      AdsManagerApp.select(cuenta);
      try {
        agregarFilasDeLaCuentaActual(filas);
      } catch (e) {
        // Una subcuenta que también es administradora (o sin acceso) no detiene las demás
        Logger.log('  Se omite ' + cuenta.getCustomerId() + ': ' + e.message);
      }
    }
  } else {
    agregarFilasDeLaCuentaActual(filas);
  }

  var hoja = SpreadsheetApp.openByUrl(URL_HOJA).getSheets()[0];
  hoja.clearContents();
  hoja.getRange(1, 1, filas.length, COLUMNAS.length).setValues(filas);
  Logger.log('TOTAL filas con datos escritas: ' + (filas.length - 1) + ' en la hoja "' + hoja.getName() + '"');
  if (filas.length === 1) {
    Logger.log('AVISO: no hay métricas en el rango. Revisa FECHA_INICIO o si las campañas tuvieron inversión.');
  }
}

function agregarFilasDeLaCuentaActual(filas) {
  var cuenta = AdsApp.currentAccount();
  var hoy = Utilities.formatDate(new Date(), cuenta.getTimeZone(), 'yyyy-MM-dd');
  var consulta =
    'SELECT segments.date, campaign.id, campaign.name, campaign.advertising_channel_type, ' +
    'campaign.status, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions ' +
    'FROM campaign ' +
    "WHERE segments.date BETWEEN '" + FECHA_INICIO + "' AND '" + hoy + "'";
  var antes = filas.length;
  var resultado = AdsApp.search(consulta);
  while (resultado.hasNext()) {
    var r = resultado.next();
    filas.push([
      r.segments.date, cuenta.getCustomerId(), cuenta.getName(), r.campaign.id, r.campaign.name,
      r.campaign.advertisingChannelType, r.campaign.status, r.metrics.costMicros || 0,
      r.metrics.impressions || 0, r.metrics.clicks || 0, r.metrics.conversions || 0
    ]);
  }
  Logger.log('  ' + cuenta.getName() + ' (' + cuenta.getCustomerId() + '): ' + (filas.length - antes) + ' filas');
}
