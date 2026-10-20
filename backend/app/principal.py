from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as ExcepcionHTTP
from sqlalchemy import func, inspect, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .configuracion import obtener_configuracion
from .base_datos import obtener_bd
from . import modelos as m, esquemas as s
from .inventario import aplicar_movimiento, asegurar_existencia, requerir
from .seguridad import HASH_FICTICIO, administrador, acceso_sucursal, usuario_actual, gestor_claves, crear_token

app = FastAPI(title='MANACO · Inventario inteligente', version='1.0.0',
              description='API de inventario por sucursal. Cantidades en pares y moneda de referencia BOB. '
                          'Reconocimiento visual pendiente de entrenamiento.',
              docs_url='/documentacion', redoc_url='/referencia', openapi_url='/esquema-api.json',
              responses={422: {'model': s.ErrorValidacion, 'description': 'Datos de entrada no válidos'}})
app.add_middleware(CORSMiddleware, allow_origins=obtener_configuracion().origenes_cors,
                   allow_credentials=False, allow_methods=['GET', 'POST', 'PUT', 'PATCH'],
                   allow_headers=['Authorization', 'Content-Type'])
BD = Annotated[Session, Depends(obtener_bd)]
Autenticado = Annotated[m.Usuario, Depends(usuario_actual)]
Administrador = Annotated[m.Usuario, Depends(administrador)]
Desplazamiento = Annotated[int, Query(ge=0)]
Limite = Annotated[int, Query(ge=1, le=200)]


def serializar(objeto, excluir=()):
    return {atributo.key: getattr(objeto, atributo.key) for atributo in inspect(type(objeto)).column_attrs
            if atributo.key not in excluir}


def serializar_usuario(usuario):
    return serializar(usuario, ('clave_hash', 'version_token'))


def vista_variante(variante, usuario):
    return serializar(variante, () if usuario.rol == 'administrador' else ('costo_referencia', 'precio_venta'))


def filtrar_sucursal(consulta, usuario, columna, id_sucursal=None):
    if id_sucursal is not None:
        acceso_sucursal(usuario, id_sucursal)
        return consulta.where(columna == id_sucursal)
    return consulta if usuario.rol == 'administrador' else consulta.where(columna == usuario.id_sucursal)


@app.exception_handler(IntegrityError)
async def error_integridad(request: Request, exc: IntegrityError):
    return JSONResponse(status_code=409, content={'detalle': 'Conflicto: código duplicado o referencia inválida'})


@app.exception_handler(ExcepcionHTTP)
async def error_http(solicitud: Request, excepcion: ExcepcionHTTP):
    mensajes = {'Not Found': 'Ruta no encontrada', 'Method Not Allowed': 'Método no permitido',
                'Not authenticated': 'Debe iniciar sesión'}
    return JSONResponse(status_code=excepcion.status_code,
                        content={'detalle': mensajes.get(str(excepcion.detail), excepcion.detail)},
                        headers=excepcion.headers)


@app.exception_handler(RequestValidationError)
async def error_validacion(solicitud: Request, excepcion: RequestValidationError):
    mensajes = {
        'missing': 'Campo obligatorio', 'extra_forbidden': 'Campo no permitido',
        'string_too_short': 'El texto no alcanza la longitud mínima',
        'string_too_long': 'El texto supera la longitud máxima',
        'string_pattern_mismatch': 'El texto no tiene el formato permitido',
        'int_parsing': 'Debe ingresar un número entero', 'int_type': 'Debe ingresar un número entero',
        'int_from_float': 'La cantidad debe ser un número entero',
        'greater_than': 'El número debe superar el mínimo permitido',
        'greater_than_equal': 'El número es inferior al mínimo permitido',
        'less_than_equal': 'El número supera el máximo permitido',
        'literal_error': 'El valor no pertenece a las opciones permitidas',
        'url_parsing': 'La dirección no es válida', 'url_scheme': 'Use una dirección HTTP o HTTPS',
        'bool_parsing': 'Debe indicar verdadero o falso', 'json_invalid': 'El contenido JSON no es válido',
        'decimal_parsing': 'Debe ingresar un número decimal válido',
        'decimal_max_digits': 'El número supera la cantidad de dígitos permitida',
        'decimal_max_places': 'El número supera la cantidad de decimales permitida',
    }
    errores = []
    for error in excepcion.errors():
        tipo = error['type']
        mensaje = mensajes.get(tipo, 'Valor no válido para este campo')
        if tipo == 'value_error' and isinstance(error.get('ctx', {}).get('error'), ValueError):
            mensaje = str(error['ctx']['error'])
        ubicacion = [({'body': 'cuerpo', 'query': 'consulta', 'path': 'ruta', 'header': 'cabecera'}).get(str(x), x)
                     for x in error['loc']]
        errores.append({'ubicacion': ubicacion, 'mensaje': mensaje})
    return JSONResponse(status_code=422, content={'detalle': errores})


@app.get('/salud', tags=['Sistema'])
def salud(base_datos: BD):
    base_datos.execute(text('SELECT 1'))
    return {'estado': 'correcto', 'version': '1.0.0'}


@app.post('/autenticacion/iniciar-sesion', tags=['Autenticación'])
def iniciar_sesion(formulario: s.Credenciales, base_datos: BD):
    usuario = base_datos.scalar(select(m.Usuario).where(m.Usuario.nombre_usuario == formulario.nombre_usuario))
    correcta = gestor_claves.verify(formulario.contrasena, usuario.clave_hash if usuario else HASH_FICTICIO)
    if not usuario or not correcta or not usuario.activo:
        raise HTTPException(401, 'Credenciales incorrectas', headers={'WWW-Authenticate': 'Bearer'})
    return {'token_acceso': crear_token(usuario), 'tipo_token': 'bearer',
            'expira_en_segundos': obtener_configuracion().minutos_token * 60, 'usuario': serializar_usuario(usuario)}


@app.get('/autenticacion/mi-perfil', tags=['Autenticación'])
def mi_perfil(usuario: Autenticado):
    return serializar_usuario(usuario)


@app.post('/autenticacion/cerrar-sesion', tags=['Autenticación'])
def cerrar_sesion(base_datos: BD, usuario: Autenticado):
    base_datos.execute(update(m.Usuario).where(m.Usuario.id == usuario.id).values(version_token=m.Usuario.version_token + 1))
    base_datos.commit()
    return {'detalle': 'Todas las sesiones del usuario fueron cerradas'}


@app.post('/autenticacion/cambiar-contrasena', tags=['Autenticación'])
def cambiar_contrasena(datos: s.CambiarContrasena, base_datos: BD, usuario: Autenticado):
    if not gestor_claves.verify(datos.contrasena_actual, usuario.clave_hash):
        raise HTTPException(400, 'Contraseña actual incorrecta')
    usuario.clave_hash = gestor_claves.hash(datos.contrasena_nueva)
    usuario.version_token += 1
    base_datos.commit()
    return {'detalle': 'Contraseña cambiada; vuelva a iniciar sesión'}


@app.post('/usuarios', status_code=201, tags=['Usuarios'])
def crear_usuario(datos: s.CrearUsuario, base_datos: BD, usuario: Administrador):
    if datos.id_sucursal is not None:
        requerir(base_datos, m.Sucursal, datos.id_sucursal)
    registro = m.Usuario(**datos.model_dump(exclude={'contrasena'}), clave_hash=gestor_claves.hash(datos.contrasena))
    base_datos.add(registro)
    base_datos.commit()
    return serializar_usuario(registro)


@app.get('/usuarios', tags=['Usuarios'])
def listar_usuarios(base_datos: BD, usuario: Administrador, desplazamiento: Desplazamiento = 0, limite: Limite = 50):
    return [serializar_usuario(x) for x in base_datos.scalars(select(m.Usuario).order_by(m.Usuario.id).offset(desplazamiento).limit(limite))]


@app.patch('/usuarios/{id_usuario}/activo', tags=['Usuarios'])
def activar_usuario(id_usuario: int, datos: s.ActualizarActivo, base_datos: BD, usuario: Administrador):
    if id_usuario == usuario.id and not datos.activo:
        raise HTTPException(409, 'No puede desactivar su propia cuenta')
    destino = requerir(base_datos, m.Usuario, id_usuario)
    destino.activo = datos.activo
    destino.version_token += 1
    base_datos.commit()
    return serializar_usuario(destino)


@app.post('/sucursales', status_code=201, tags=['Sucursales'])
def crear_sucursal(datos: s.CrearSucursal, base_datos: BD, usuario: Administrador):
    registro = m.Sucursal(**datos.model_dump())
    base_datos.add(registro)
    base_datos.commit()
    return serializar(registro)


@app.get('/sucursales', tags=['Sucursales'])
def sucursales(base_datos: BD, usuario: Autenticado):
    # El operador puede ver destinos para preparar transferencias.
    return [serializar(x) for x in base_datos.scalars(select(m.Sucursal).order_by(m.Sucursal.id))]


@app.post('/productos', status_code=201, tags=['Catálogo'])
def crear_producto(datos: s.CrearProducto, base_datos: BD, usuario: Administrador):
    valores = datos.model_dump()
    valores['url_foto'] = str(datos.url_foto) if datos.url_foto else None
    registro = m.Producto(**valores)
    base_datos.add(registro)
    base_datos.commit()
    return serializar(registro)


@app.get('/productos', tags=['Catálogo'])
def listar_productos(base_datos: BD, usuario: Autenticado, buscar: str | None = Query(default=None, max_length=100),
             desplazamiento: Desplazamiento = 0, limite: Limite = 50):
    consulta = select(m.Producto)
    if buscar:
        consulta = consulta.where(or_(m.Producto.nombre.ilike(f'%{buscar}%'), m.Producto.codigo.ilike(f'%{buscar}%')))
    return [serializar(x) for x in base_datos.scalars(consulta.order_by(m.Producto.id).offset(desplazamiento).limit(limite))]


@app.get('/productos/{id_producto}', tags=['Catálogo'])
def producto(id_producto: int, base_datos: BD, usuario: Autenticado):
    return serializar(requerir(base_datos, m.Producto, id_producto))


@app.put('/productos/{id_producto}', tags=['Catálogo'])
def actualizar_producto(id_producto: int, datos: s.ActualizarProducto, base_datos: BD, usuario: Administrador):
    registro = requerir(base_datos, m.Producto, id_producto)
    for key, value in datos.model_dump().items():
        setattr(registro, key, str(value) if key == 'url_foto' and value is not None else value)
    base_datos.commit()
    return serializar(registro)


@app.post('/variantes', status_code=201, tags=['Catálogo'])
def crear_variante(datos: s.CrearVariante, base_datos: BD, usuario: Administrador):
    requerir(base_datos, m.Producto, datos.id_producto)
    registro = m.Variante(**datos.model_dump())
    base_datos.add(registro)
    base_datos.commit()
    return vista_variante(registro, usuario)


@app.get('/variantes', tags=['Catálogo'])
def listar_variantes(base_datos: BD, usuario: Autenticado, id_producto: int | None = Query(default=None, gt=0),
             desplazamiento: Desplazamiento = 0, limite: Limite = 50):
    consulta = select(m.Variante)
    if id_producto:
        consulta = consulta.where(m.Variante.id_producto == id_producto)
    return [vista_variante(x, usuario) for x in base_datos.scalars(consulta.order_by(m.Variante.id).offset(desplazamiento).limit(limite))]


@app.get('/existencias', tags=['Inventario'])
def listar_existencias(base_datos: BD, usuario: Autenticado, id_sucursal: int | None = Query(default=None, gt=0),
           solo_bajo_minimo: bool = False, desplazamiento: Desplazamiento = 0, limite: Limite = 50):
    consulta = select(m.Existencia, m.Variante, m.Producto).join(
        m.Variante, m.Existencia.id_variante == m.Variante.id).join(m.Producto, m.Variante.id_producto == m.Producto.id)
    consulta = filtrar_sucursal(consulta, usuario, m.Existencia.id_sucursal, id_sucursal)
    if solo_bajo_minimo:
        consulta = consulta.where(m.Existencia.cantidad <= m.Existencia.cantidad_minima)
    return [{**serializar(existencia), 'codigo_variante': variante.codigo_variante, 'talla': variante.talla, 'color': variante.color,
             'nombre_producto': producto.nombre, 'bajo_minimo': existencia.cantidad <= existencia.cantidad_minima}
            for existencia, variante, producto in base_datos.execute(consulta.order_by(m.Existencia.id).offset(desplazamiento).limit(limite))]


@app.put('/existencias/{id_sucursal}/{id_variante}/minimo', tags=['Inventario'])
def minimo_existencia(id_sucursal: int, id_variante: int, datos: s.MinimoExistencia, base_datos: BD, usuario: Administrador):
    registro = asegurar_existencia(base_datos, id_sucursal, id_variante)
    registro.cantidad_minima = datos.cantidad_minima
    base_datos.commit()
    return serializar(registro)


@app.post('/movimientos', status_code=201, tags=['Movimientos'])
def crear_movimiento(datos: s.CrearMovimiento, base_datos: BD, usuario: Autenticado):
    acceso_sucursal(usuario, datos.id_sucursal)
    variacion_cantidad = datos.cantidad if datos.tipo == 'entrada' else -datos.cantidad
    registro = aplicar_movimiento(base_datos, datos.id_sucursal, datos.id_variante, variacion_cantidad, datos.tipo, datos.motivo, usuario.id)
    base_datos.commit()
    return serializar(registro)


@app.get('/movimientos', tags=['Movimientos'])
def listar_movimientos(base_datos: BD, usuario: Autenticado, id_sucursal: int | None = Query(default=None, gt=0),
              id_variante: int | None = Query(default=None, gt=0), desplazamiento: Desplazamiento = 0, limite: Limite = 50):
    consulta = filtrar_sucursal(select(m.Movimiento), usuario, m.Movimiento.id_sucursal, id_sucursal)
    if id_variante:
        consulta = consulta.where(m.Movimiento.id_variante == id_variante)
    return [serializar(x) for x in base_datos.scalars(consulta.order_by(m.Movimiento.id.desc()).offset(desplazamiento).limit(limite))]


@app.post('/transferencias', status_code=201, tags=['Transferencias'])
def crear_transferencia(datos: s.CrearTransferencia, base_datos: BD, usuario: Autenticado):
    acceso_sucursal(usuario, datos.id_sucursal_origen)
    destino = requerir(base_datos, m.Sucursal, datos.id_sucursal_destino)
    if not destino.activo:
        raise HTTPException(409, 'Sucursal destino inactiva')
    registro = m.Transferencia(**datos.model_dump(), id_creador=usuario.id)
    base_datos.add(registro)
    base_datos.flush()
    aplicar_movimiento(base_datos, datos.id_sucursal_origen, datos.id_variante, -datos.cantidad, 'salida_transferencia',
                   'Envío a sucursal', usuario.id, id_transferencia=registro.id)
    base_datos.commit()
    return serializar(registro)


@app.get('/transferencias', tags=['Transferencias'])
def listar_transferencias(base_datos: BD, usuario: Autenticado, desplazamiento: Desplazamiento = 0, limite: Limite = 50):
    consulta = select(m.Transferencia)
    if usuario.rol != 'administrador':
        consulta = consulta.where(or_(m.Transferencia.id_sucursal_origen == usuario.id_sucursal, m.Transferencia.id_sucursal_destino == usuario.id_sucursal))
    return [serializar(x) for x in base_datos.scalars(consulta.order_by(m.Transferencia.id.desc()).offset(desplazamiento).limit(limite))]


@app.post('/transferencias/{id_transferencia}/recibir', tags=['Transferencias'])
def recibir_transferencia(id_transferencia: int, base_datos: BD, usuario: Autenticado):
    registro = base_datos.scalar(select(m.Transferencia).where(m.Transferencia.id == id_transferencia).with_for_update())
    if registro is None:
        raise HTTPException(404, 'Transferencia no encontrada')
    acceso_sucursal(usuario, registro.id_sucursal_destino)
    # Actualización condicional también impide recibir dos veces bajo concurrencia.
    resultado = base_datos.execute(update(m.Transferencia).where(m.Transferencia.id == id_transferencia, m.Transferencia.estado == 'en_transito')
                        .values(estado='recibida', id_receptor=usuario.id, fecha_recepcion=m.fecha_actual()),
                        execution_options={'synchronize_session': False})
    if resultado.rowcount != 1:
        raise HTTPException(409, 'La transferencia ya fue recibida')
    aplicar_movimiento(base_datos, registro.id_sucursal_destino, registro.id_variante, registro.cantidad, 'entrada_transferencia',
                   'Recepción desde sucursal', usuario.id, id_transferencia=registro.id)
    base_datos.commit()
    base_datos.refresh(registro)
    return serializar(registro)


@app.post('/ajustes', status_code=201, tags=['Ajustes'])
def solicitar_ajuste(datos: s.CrearAjuste, base_datos: BD, usuario: Autenticado):
    acceso_sucursal(usuario, datos.id_sucursal)
    asegurar_existencia(base_datos, datos.id_sucursal, datos.id_variante)
    registro = m.Ajuste(**datos.model_dump(), id_solicitante=usuario.id)
    base_datos.add(registro)
    base_datos.commit()
    return serializar(registro)


@app.get('/ajustes', tags=['Ajustes'])
def listar_ajustes(base_datos: BD, usuario: Autenticado, desplazamiento: Desplazamiento = 0, limite: Limite = 50):
    consulta = filtrar_sucursal(select(m.Ajuste), usuario, m.Ajuste.id_sucursal)
    return [serializar(x) for x in base_datos.scalars(consulta.order_by(m.Ajuste.id.desc()).offset(desplazamiento).limit(limite))]


@app.post('/ajustes/{id_ajuste}/revisar', tags=['Ajustes'])
def revisar_ajuste(id_ajuste: int, datos: s.RevisarAjuste, base_datos: BD, usuario: Administrador):
    registro = base_datos.scalar(select(m.Ajuste).where(m.Ajuste.id == id_ajuste).with_for_update())
    if registro is None:
        raise HTTPException(404, 'Ajuste no encontrado')
    resultado = base_datos.execute(update(m.Ajuste).where(m.Ajuste.id == id_ajuste, m.Ajuste.estado == 'pendiente')
                        .values(estado=datos.decision, id_revisor=usuario.id, fecha_revision=m.fecha_actual()),
                        execution_options={'synchronize_session': False})
    if resultado.rowcount != 1:
        raise HTTPException(409, 'El ajuste ya fue revisado')
    if datos.decision == 'aprobado':
        aplicar_movimiento(base_datos, registro.id_sucursal, registro.id_variante, registro.variacion_cantidad, 'ajuste', registro.motivo,
                       usuario.id, id_ajuste=registro.id)
    base_datos.commit()
    base_datos.refresh(registro)
    return serializar(registro)


@app.get('/tablero', tags=['Tablero'])
def tablero(base_datos: BD, usuario: Autenticado, id_sucursal: int | None = Query(default=None, gt=0)):
    base = filtrar_sucursal(select(m.Existencia.id_sucursal.label('id_sucursal'), m.Existencia.id_variante.label('id_variante'),
                        m.Existencia.cantidad.label('cantidad'), m.Existencia.cantidad_minima.label('cantidad_minima')),
                 usuario, m.Existencia.id_sucursal, id_sucursal).subquery()
    total = base_datos.scalar(select(func.coalesce(func.sum(base.c.cantidad), 0)))
    bajas = base_datos.scalar(select(func.count()).select_from(base).where(base.c.cantidad <= base.c.cantidad_minima))
    pendientes = filtrar_sucursal(select(m.Ajuste), usuario, m.Ajuste.id_sucursal, id_sucursal).where(m.Ajuste.estado == 'pendiente')
    consulta_transferencias = select(m.Transferencia).where(m.Transferencia.estado == 'en_transito')
    seleccionada = id_sucursal if id_sucursal is not None else (usuario.id_sucursal if usuario.rol != 'administrador' else None)
    if seleccionada is not None:
        consulta_transferencias = consulta_transferencias.where(or_(m.Transferencia.id_sucursal_origen == seleccionada, m.Transferencia.id_sucursal_destino == seleccionada))
    transito = base_datos.scalar(select(func.coalesce(func.sum(consulta_transferencias.with_only_columns(
        m.Transferencia.cantidad.label('cantidad')).subquery().c.cantidad), 0)))
    resultado = {'pares_disponibles': total, 'existencias_bajo_minimo': bajas, 'pares_en_transito': transito,
              'ajustes_pendientes': base_datos.scalar(select(func.count()).select_from(pendientes.subquery())),
              'productos_activos': base_datos.scalar(select(func.count()).select_from(m.Producto).where(m.Producto.activo)),
              'estado_reconocimiento': 'sin_entrenar'}
    if usuario.rol == 'administrador':
        resultado['valor_estimado_inventario_bob'] = base_datos.scalar(select(func.coalesce(
            func.sum(base.c.cantidad * m.Variante.costo_referencia), 0)).select_from(base).join(
                m.Variante, base.c.id_variante == m.Variante.id))
    return resultado


@app.get('/reconocimiento/estado', tags=['Reconocimiento'])
def estado_reconocimiento(usuario: Autenticado):
    return {'disponible': False, 'estado': 'sin_entrenar',
            'detalle': 'Pendiente: fotografías etiquetadas, entrenamiento y evaluación del modelo.'}
