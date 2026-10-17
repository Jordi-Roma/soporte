from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class Entrada(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Credenciales(BaseModel):
    model_config = ConfigDict(extra='forbid')
    nombre_usuario: str = Field(min_length=1, max_length=50)
    contrasena: str = Field(min_length=1, max_length=128)


class DetalleValidacion(BaseModel):
    ubicacion: list[str | int]
    mensaje: str


class ErrorValidacion(BaseModel):
    detalle: list[DetalleValidacion]


class CrearSucursal(Entrada):
    nombre: str = Field(min_length=2, max_length=100)
    direccion: str = Field(default='', max_length=250)


class CrearUsuario(Entrada):
    nombre_usuario: str = Field(pattern=r'^[a-zA-Z0-9_.-]{3,50}$')
    nombre_completo: str = Field(min_length=2, max_length=120)
    contrasena: str = Field(min_length=12, max_length=128)
    rol: Literal['administrador', 'operador'] = 'operador'
    id_sucursal: int | None = Field(default=None, gt=0)

    @model_validator(mode='after')
    def sucursal_operador(self):
        if self.rol == 'operador' and self.id_sucursal is None:
            raise ValueError('El operador necesita una sucursal')
        return self


class ActualizarActivo(Entrada):
    activo: bool


class CambiarContrasena(Entrada):
    contrasena_actual: str = Field(max_length=128)
    contrasena_nueva: str = Field(min_length=12, max_length=128)


class CrearProducto(Entrada):
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=2, max_length=150)
    categoria: str = Field(min_length=2, max_length=100)
    descripcion: str = Field(default='', max_length=1000)
    url_foto: HttpUrl | None = None


class ActualizarProducto(Entrada):
    nombre: str = Field(min_length=2, max_length=150)
    categoria: str = Field(min_length=2, max_length=100)
    descripcion: str = Field(default='', max_length=1000)
    url_foto: HttpUrl | None = None
    activo: bool = True


class CrearVariante(Entrada):
    id_producto: int = Field(gt=0)
    codigo_variante: str = Field(min_length=1, max_length=80)
    talla: str = Field(min_length=1, max_length=20)
    color: str = Field(min_length=1, max_length=50)
    costo_referencia: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    precio_venta: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)


class MinimoExistencia(Entrada):
    cantidad_minima: int = Field(ge=0, le=1000000)


class CrearMovimiento(Entrada):
    id_sucursal: int = Field(gt=0)
    id_variante: int = Field(gt=0)
    tipo: Literal['entrada', 'salida']
    cantidad: int = Field(gt=0, le=1000000)
    motivo: str = Field(min_length=3, max_length=500)


class CrearTransferencia(Entrada):
    id_sucursal_origen: int = Field(gt=0)
    id_sucursal_destino: int = Field(gt=0)
    id_variante: int = Field(gt=0)
    cantidad: int = Field(gt=0, le=1000000)
    observacion: str = Field(default='', max_length=500)

    @model_validator(mode='after')
    def sucursales_diferentes(self):
        if self.id_sucursal_origen == self.id_sucursal_destino:
            raise ValueError('Origen y destino deben ser diferentes')
        return self


class CrearAjuste(Entrada):
    id_sucursal: int = Field(gt=0)
    id_variante: int = Field(gt=0)
    variacion_cantidad: int = Field(ge=-1000000, le=1000000)
    motivo: str = Field(min_length=5, max_length=500)

    @model_validator(mode='after')
    def distinto_de_cero(self):
        if self.variacion_cantidad == 0:
            raise ValueError('El ajuste debe ser diferente de cero')
        return self


class RevisarAjuste(Entrada):
    decision: Literal['aprobado', 'rechazado']
