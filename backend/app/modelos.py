from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base_datos import Base


def fecha_actual():
    return datetime.now(timezone.utc)


class Sucursal(Base):
    __tablename__ = 'sucursales'
    id: Mapped[int] = mapped_column('id_sucursal', primary_key=True)
    nombre: Mapped[str] = mapped_column('nombre', String(100), unique=True)
    direccion: Mapped[str] = mapped_column('direccion', String(250), default='')
    activo: Mapped[bool] = mapped_column('activo', Boolean, default=True)


class Usuario(Base):
    __tablename__ = 'usuarios'
    id: Mapped[int] = mapped_column('id_usuario', primary_key=True)
    nombre_usuario: Mapped[str] = mapped_column('nombre_usuario', String(50), unique=True)
    nombre_completo: Mapped[str] = mapped_column('nombre_completo', String(120))
    clave_hash: Mapped[str] = mapped_column('clave_hash', String(255))
    rol: Mapped[str] = mapped_column('rol', String(20))
    id_sucursal: Mapped[int | None] = mapped_column('id_sucursal', ForeignKey('sucursales.id_sucursal'))
    activo: Mapped[bool] = mapped_column('activo', Boolean, default=True)
    version_token: Mapped[int] = mapped_column('version_token', Integer, default=0)
    __table_args__ = (CheckConstraint("rol IN ('administrador','operador')"),
                      CheckConstraint("rol != 'operador' OR id_sucursal IS NOT NULL"))


class Producto(Base):
    __tablename__ = 'productos'
    id: Mapped[int] = mapped_column('id_producto', primary_key=True)
    codigo: Mapped[str] = mapped_column('codigo', String(50), unique=True)
    nombre: Mapped[str] = mapped_column('nombre', String(150))
    categoria: Mapped[str] = mapped_column('categoria', String(100))
    descripcion: Mapped[str] = mapped_column('descripcion', String(1000), default='')
    url_foto: Mapped[str | None] = mapped_column('url_foto', String(1000))
    activo: Mapped[bool] = mapped_column('activo', Boolean, default=True)


class Variante(Base):
    __tablename__ = 'variantes'
    id: Mapped[int] = mapped_column('id_variante', primary_key=True)
    id_producto: Mapped[int] = mapped_column('id_producto', ForeignKey('productos.id_producto'))
    codigo_variante: Mapped[str] = mapped_column('codigo_variante', String(80), unique=True)
    talla: Mapped[str] = mapped_column('talla', String(20))
    color: Mapped[str] = mapped_column(String(50))
    costo_referencia: Mapped[Decimal] = mapped_column('costo_referencia', Numeric(12, 2), default=0)
    precio_venta: Mapped[Decimal] = mapped_column('precio_venta', Numeric(12, 2), default=0)
    activo: Mapped[bool] = mapped_column('activo', Boolean, default=True)
    __table_args__ = (UniqueConstraint('id_producto', 'talla', 'color'),
                      CheckConstraint('costo_referencia >= 0 AND precio_venta >= 0'))


class Existencia(Base):
    __tablename__ = 'existencias'
    id: Mapped[int] = mapped_column('id_existencia', primary_key=True)
    id_sucursal: Mapped[int] = mapped_column('id_sucursal', ForeignKey('sucursales.id_sucursal'))
    id_variante: Mapped[int] = mapped_column('id_variante', ForeignKey('variantes.id_variante'))
    cantidad: Mapped[int] = mapped_column('cantidad', Integer, default=0)
    cantidad_minima: Mapped[int] = mapped_column('cantidad_minima', Integer, default=0)
    __table_args__ = (UniqueConstraint('id_sucursal', 'id_variante'),
                      CheckConstraint('cantidad >= 0 AND cantidad_minima >= 0'))


class Transferencia(Base):
    __tablename__ = 'transferencias'
    id: Mapped[int] = mapped_column('id_transferencia', primary_key=True)
    id_sucursal_origen: Mapped[int] = mapped_column('id_sucursal_origen', ForeignKey('sucursales.id_sucursal'))
    id_sucursal_destino: Mapped[int] = mapped_column('id_sucursal_destino', ForeignKey('sucursales.id_sucursal'))
    id_variante: Mapped[int] = mapped_column('id_variante', ForeignKey('variantes.id_variante'))
    cantidad: Mapped[int] = mapped_column('cantidad', Integer)
    estado: Mapped[str] = mapped_column('estado', String(20), default='en_transito')
    id_creador: Mapped[int] = mapped_column('id_creador', ForeignKey('usuarios.id_usuario'))
    id_receptor: Mapped[int | None] = mapped_column('id_receptor', ForeignKey('usuarios.id_usuario'))
    fecha_creacion: Mapped[datetime] = mapped_column('fecha_envio', DateTime(timezone=True), default=fecha_actual)
    fecha_recepcion: Mapped[datetime | None] = mapped_column('fecha_recepcion', DateTime(timezone=True))
    observacion: Mapped[str] = mapped_column('observacion', String(500), default='')
    __table_args__ = (CheckConstraint('cantidad > 0 AND id_sucursal_origen != id_sucursal_destino'),
                      CheckConstraint("estado IN ('en_transito','recibida')"))


class Movimiento(Base):
    __tablename__ = 'movimientos'
    id: Mapped[int] = mapped_column('id_movimiento', primary_key=True)
    id_sucursal: Mapped[int] = mapped_column('id_sucursal', ForeignKey('sucursales.id_sucursal'))
    id_variante: Mapped[int] = mapped_column('id_variante', ForeignKey('variantes.id_variante'))
    variacion_cantidad: Mapped[int] = mapped_column('variacion_cantidad', Integer)
    tipo: Mapped[str] = mapped_column('tipo', String(30))
    motivo: Mapped[str] = mapped_column('motivo', String(500))
    id_usuario: Mapped[int] = mapped_column('id_usuario', ForeignKey('usuarios.id_usuario'))
    id_transferencia: Mapped[int | None] = mapped_column('id_transferencia', ForeignKey('transferencias.id_transferencia'))
    id_ajuste: Mapped[int | None] = mapped_column('id_ajuste', ForeignKey('ajustes.id_ajuste'))
    fecha_creacion: Mapped[datetime] = mapped_column('fecha_creacion', DateTime(timezone=True), default=fecha_actual)
    __table_args__ = (CheckConstraint('variacion_cantidad != 0'),)


class Ajuste(Base):
    __tablename__ = 'ajustes'
    id: Mapped[int] = mapped_column('id_ajuste', primary_key=True)
    id_sucursal: Mapped[int] = mapped_column('id_sucursal', ForeignKey('sucursales.id_sucursal'))
    id_variante: Mapped[int] = mapped_column('id_variante', ForeignKey('variantes.id_variante'))
    variacion_cantidad: Mapped[int] = mapped_column('variacion_cantidad', Integer)
    motivo: Mapped[str] = mapped_column('motivo', String(500))
    estado: Mapped[str] = mapped_column('estado', String(20), default='pendiente')
    id_solicitante: Mapped[int] = mapped_column('id_solicitante', ForeignKey('usuarios.id_usuario'))
    id_revisor: Mapped[int | None] = mapped_column('id_revisor', ForeignKey('usuarios.id_usuario'))
    fecha_creacion: Mapped[datetime] = mapped_column('fecha_solicitud', DateTime(timezone=True), default=fecha_actual)
    fecha_revision: Mapped[datetime | None] = mapped_column('fecha_revision', DateTime(timezone=True))
    __table_args__ = (CheckConstraint('variacion_cantidad != 0'),
                      CheckConstraint("estado IN ('pendiente','aprobado','rechazado')"))
