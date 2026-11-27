-- M1 - Data Mart comercial de Reciel: esquema estrella
-- Se puede ejecutar varias veces: borra y vuelve a crear las tablas (¡se pierden los datos cargados!).

USE dm_comercial;

DROP TABLE IF EXISTS Hecho_Ventas;
DROP TABLE IF EXISTS Hecho_Campanas;
DROP TABLE IF EXISTS Dim_Cliente;
DROP TABLE IF EXISTS Dim_Producto;
DROP TABLE IF EXISTS Dim_Tiempo;
DROP TABLE IF EXISTS Dim_Campana;
DROP TABLE IF EXISTS Dim_Vendedor;
DROP TABLE IF EXISTS etl_log;

CREATE TABLE Dim_Cliente (
  SK_Cliente INT AUTO_INCREMENT PRIMARY KEY,
  RUC VARCHAR(11) NOT NULL UNIQUE,
  Razon_Social VARCHAR(255),
  Nombre_Comercial VARCHAR(255),
  Sector_Economico VARCHAR(100),
  Origen_Datos VARCHAR(50)
);

CREATE TABLE Dim_Producto (
  SK_Producto INT AUTO_INCREMENT PRIMARY KEY,
  SKU_Producto VARCHAR(100) NOT NULL UNIQUE,
  Descripcion VARCHAR(255),
  Talla VARCHAR(20),
  Categoria VARCHAR(100),
  Tipo_Proteccion VARCHAR(100)
);

CREATE TABLE Dim_Tiempo (
  SK_Tiempo INT PRIMARY KEY,
  Fecha DATE NOT NULL UNIQUE,
  Anio SMALLINT,
  Trimestre TINYINT,
  Mes TINYINT,
  Nombre_Mes VARCHAR(20),
  Dia TINYINT,
  Campana_Agricola VARCHAR(50)
);

CREATE TABLE Dim_Campana (
  SK_Campana INT AUTO_INCREMENT PRIMARY KEY,
  ID_Campana_Origen VARCHAR(100) UNIQUE,
  Nombre_Campana VARCHAR(255),
  Plataforma VARCHAR(50),
  Tipo_Estrategia VARCHAR(50)
);

CREATE TABLE Dim_Vendedor (
  SK_Vendedor INT AUTO_INCREMENT PRIMARY KEY,
  ID_HubSpot_Owner VARCHAR(50) UNIQUE,
  Nombre_Completo VARCHAR(150),
  Email VARCHAR(100)
);

-- Registros por defecto (clave 0) para ventas sin campaña o sin vendedor asignado
SET SESSION sql_mode = CONCAT(@@sql_mode, ',NO_AUTO_VALUE_ON_ZERO');
INSERT INTO Dim_Campana (SK_Campana, ID_Campana_Origen, Nombre_Campana, Plataforma)
VALUES (0, 'N/A', 'Sin campaña', 'Directo');
INSERT INTO Dim_Vendedor (SK_Vendedor, ID_HubSpot_Owner, Nombre_Completo)
VALUES (0, 'N/A', 'Sin asignar');

CREATE TABLE Hecho_Ventas (
  SK_Venta INT AUTO_INCREMENT PRIMARY KEY,
  SK_Cliente INT NOT NULL,
  SK_Producto INT NOT NULL,
  SK_Tiempo INT NOT NULL,
  SK_Vendedor INT NOT NULL DEFAULT 0,
  SK_Campana INT NOT NULL DEFAULT 0,
  Origen_Factura VARCHAR(20),
  Serie_Factura VARCHAR(10) NOT NULL,
  Numero_Factura VARCHAR(20) NOT NULL,
  Linea_Factura SMALLINT NOT NULL,
  Numero_Orden_Compra VARCHAR(50),
  Cantidad_Vendida DECIMAL(12,2),
  Precio_Unitario_Sin_IGV DECIMAL(12,2),
  Monto_Neto DECIMAL(14,2),
  Monto_IGV DECIMAL(14,2),
  Monto_Total_Facturado DECIMAL(14,2),
  UNIQUE KEY uq_linea_factura (Serie_Factura, Numero_Factura, Linea_Factura),
  FOREIGN KEY (SK_Cliente) REFERENCES Dim_Cliente(SK_Cliente),
  FOREIGN KEY (SK_Producto) REFERENCES Dim_Producto(SK_Producto),
  FOREIGN KEY (SK_Tiempo) REFERENCES Dim_Tiempo(SK_Tiempo),
  FOREIGN KEY (SK_Vendedor) REFERENCES Dim_Vendedor(SK_Vendedor),
  FOREIGN KEY (SK_Campana) REFERENCES Dim_Campana(SK_Campana)
);

CREATE TABLE Hecho_Campanas (
  SK_Hecho_Campana INT AUTO_INCREMENT PRIMARY KEY,
  SK_Campana INT NOT NULL,
  SK_Tiempo INT NOT NULL,
  Inversion_Publicitaria DECIMAL(12,2),
  Impresiones INT,
  Clics INT,
  Cotizaciones_Generadas INT,
  UNIQUE KEY uq_campana_dia (SK_Campana, SK_Tiempo),
  FOREIGN KEY (SK_Campana) REFERENCES Dim_Campana(SK_Campana),
  FOREIGN KEY (SK_Tiempo) REFERENCES Dim_Tiempo(SK_Tiempo)
);

CREATE TABLE etl_log (
  id INT AUTO_INCREMENT PRIMARY KEY,
  fecha_ejecucion DATETIME DEFAULT CURRENT_TIMESTAMP,
  proceso VARCHAR(50),
  filas_cargadas INT,
  estado VARCHAR(20),
  detalle TEXT
);
