-- Esquema MANACO en español. Ejecutar dentro de una base vacía.


CREATE TABLE sucursales (
	id_sucursal SERIAL NOT NULL,
	nombre VARCHAR(100) NOT NULL,
	direccion VARCHAR(250) NOT NULL,
	activo BOOLEAN NOT NULL,
	PRIMARY KEY (id_sucursal),
	UNIQUE (nombre)
)

;


CREATE TABLE productos (
	id_producto SERIAL NOT NULL,
	codigo VARCHAR(50) NOT NULL,
	nombre VARCHAR(150) NOT NULL,
	categoria VARCHAR(100) NOT NULL,
	descripcion VARCHAR(1000) NOT NULL,
	url_foto VARCHAR(1000),
	activo BOOLEAN NOT NULL,
	PRIMARY KEY (id_producto),
	UNIQUE (codigo)
)

;


CREATE TABLE usuarios (
	id_usuario SERIAL NOT NULL,
	nombre_usuario VARCHAR(50) NOT NULL,
	nombre_completo VARCHAR(120) NOT NULL,
	clave_hash VARCHAR(255) NOT NULL,
	rol VARCHAR(20) NOT NULL,
	id_sucursal INTEGER,
	activo BOOLEAN NOT NULL,
	version_token INTEGER NOT NULL,
	PRIMARY KEY (id_usuario),
	CHECK (rol IN ('administrador','operador')),
	CHECK (rol != 'operador' OR id_sucursal IS NOT NULL),
	UNIQUE (nombre_usuario),
	FOREIGN KEY(id_sucursal) REFERENCES sucursales (id_sucursal)
)

;


CREATE TABLE variantes (
	id_variante SERIAL NOT NULL,
	id_producto INTEGER NOT NULL,
	codigo_variante VARCHAR(80) NOT NULL,
	talla VARCHAR(20) NOT NULL,
	color VARCHAR(50) NOT NULL,
	costo_referencia NUMERIC(12, 2) NOT NULL,
	precio_venta NUMERIC(12, 2) NOT NULL,
	activo BOOLEAN NOT NULL,
	PRIMARY KEY (id_variante),
	UNIQUE (id_producto, talla, color),
	CHECK (costo_referencia >= 0 AND precio_venta >= 0),
	FOREIGN KEY(id_producto) REFERENCES productos (id_producto),
	UNIQUE (codigo_variante)
)

;


CREATE TABLE existencias (
	id_existencia SERIAL NOT NULL,
	id_sucursal INTEGER NOT NULL,
	id_variante INTEGER NOT NULL,
	cantidad INTEGER NOT NULL,
	cantidad_minima INTEGER NOT NULL,
	PRIMARY KEY (id_existencia),
	UNIQUE (id_sucursal, id_variante),
	CHECK (cantidad >= 0 AND cantidad_minima >= 0),
	FOREIGN KEY(id_sucursal) REFERENCES sucursales (id_sucursal),
	FOREIGN KEY(id_variante) REFERENCES variantes (id_variante)
)

;


CREATE TABLE transferencias (
	id_transferencia SERIAL NOT NULL,
	id_sucursal_origen INTEGER NOT NULL,
	id_sucursal_destino INTEGER NOT NULL,
	id_variante INTEGER NOT NULL,
	cantidad INTEGER NOT NULL,
	estado VARCHAR(20) NOT NULL,
	id_creador INTEGER NOT NULL,
	id_receptor INTEGER,
	fecha_envio TIMESTAMP WITH TIME ZONE NOT NULL,
	fecha_recepcion TIMESTAMP WITH TIME ZONE,
	observacion VARCHAR(500) NOT NULL,
	PRIMARY KEY (id_transferencia),
	CHECK (cantidad > 0 AND id_sucursal_origen != id_sucursal_destino),
	CHECK (estado IN ('en_transito','recibida')),
	FOREIGN KEY(id_sucursal_origen) REFERENCES sucursales (id_sucursal),
	FOREIGN KEY(id_sucursal_destino) REFERENCES sucursales (id_sucursal),
	FOREIGN KEY(id_variante) REFERENCES variantes (id_variante),
	FOREIGN KEY(id_creador) REFERENCES usuarios (id_usuario),
	FOREIGN KEY(id_receptor) REFERENCES usuarios (id_usuario)
)

;


CREATE TABLE ajustes (
	id_ajuste SERIAL NOT NULL,
	id_sucursal INTEGER NOT NULL,
	id_variante INTEGER NOT NULL,
	variacion_cantidad INTEGER NOT NULL,
	motivo VARCHAR(500) NOT NULL,
	estado VARCHAR(20) NOT NULL,
	id_solicitante INTEGER NOT NULL,
	id_revisor INTEGER,
	fecha_solicitud TIMESTAMP WITH TIME ZONE NOT NULL,
	fecha_revision TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id_ajuste),
	CHECK (variacion_cantidad != 0),
	CHECK (estado IN ('pendiente','aprobado','rechazado')),
	FOREIGN KEY(id_sucursal) REFERENCES sucursales (id_sucursal),
	FOREIGN KEY(id_variante) REFERENCES variantes (id_variante),
	FOREIGN KEY(id_solicitante) REFERENCES usuarios (id_usuario),
	FOREIGN KEY(id_revisor) REFERENCES usuarios (id_usuario)
)

;


CREATE TABLE movimientos (
	id_movimiento SERIAL NOT NULL,
	id_sucursal INTEGER NOT NULL,
	id_variante INTEGER NOT NULL,
	variacion_cantidad INTEGER NOT NULL,
	tipo VARCHAR(30) NOT NULL,
	motivo VARCHAR(500) NOT NULL,
	id_usuario INTEGER NOT NULL,
	id_transferencia INTEGER,
	id_ajuste INTEGER,
	fecha_creacion TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id_movimiento),
	CHECK (variacion_cantidad != 0),
	FOREIGN KEY(id_sucursal) REFERENCES sucursales (id_sucursal),
	FOREIGN KEY(id_variante) REFERENCES variantes (id_variante),
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario),
	FOREIGN KEY(id_transferencia) REFERENCES transferencias (id_transferencia),
	FOREIGN KEY(id_ajuste) REFERENCES ajustes (id_ajuste)
)

;
