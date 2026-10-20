from decimal import Decimal
import pytest
from sqlalchemy import func, select
from app.base_datos import SesionLocal, motor
from app.modelos import Movimiento, Existencia, Transferencia


def autenticar(api, nombre_usuario='administrador', contrasena='Administrador-test-2026!'):
    respuesta = api.post('/autenticacion/iniciar-sesion', json={'nombre_usuario': nombre_usuario, 'contrasena': contrasena})
    assert respuesta.status_code == 200, respuesta.text
    return {'Authorization': 'Bearer ' + respuesta.json()['token_acceso']}


def preparar(api):
    cabeceras = autenticar(api)
    a = api.post('/sucursales', headers=cabeceras, json={'nombre': 'Central'}).json()['id']
    b = api.post('/sucursales', headers=cabeceras, json={'nombre': 'Centro'}).json()['id']
    producto = api.post('/productos', headers=cabeceras, json={
        'codigo': 'MOD-001', 'nombre': 'Escolar', 'categoria': 'Escolar'}).json()['id']
    respuesta = api.post('/variantes', headers=cabeceras, json={
        'id_producto': producto, 'codigo_variante': 'ESC-38', 'talla': '38', 'color': 'Negro',
        'costo_referencia': 100, 'precio_venta': 180})
    assert respuesta.status_code == 201, respuesta.text
    variante = respuesta.json()['id']
    for nombre, sucursal in [('operator_a', a), ('operator_b', b)]:
        assert api.post('/usuarios', headers=cabeceras, json={
            'nombre_usuario': nombre, 'nombre_completo': nombre, 'contrasena': 'Operator-test-2026!',
            'id_sucursal': sucursal}).status_code == 201
    return cabeceras, a, b, variante


def registrar_movimiento(api, cabeceras, sucursal, variante, tipo, cantidad):
    return api.post('/movimientos', headers=cabeceras, json={
        'id_sucursal': sucursal, 'id_variante': variante, 'tipo': tipo,
        'cantidad': cantidad, 'motivo': 'Movimiento de prueba'})


def test_autenticacion_permisos_y_revocacion(api):
    cabeceras, a, b, variante = preparar(api)
    assert api.get('/existencias').status_code == 401
    assert api.post('/autenticacion/iniciar-sesion', json={'nombre_usuario': 'administrador', 'contrasena': 'wrong'}).status_code == 401
    operador = autenticar(api, 'operator_a', 'Operator-test-2026!')
    assert api.get('/usuarios', headers=operador).status_code == 403
    assert api.get(f'/existencias?id_sucursal={b}', headers=operador).status_code == 403
    assert registrar_movimiento(api, operador, b, variante, 'entrada', 1).status_code == 403
    valores = api.get('/variantes', headers=operador).json()[0]
    assert 'costo_referencia' not in valores and 'precio_venta' not in valores
    assert api.post('/autenticacion/cerrar-sesion', headers=operador).status_code == 200
    assert api.get('/autenticacion/mi-perfil', headers=operador).status_code == 401


def test_existencias_negativas_e_historial(api):
    cabeceras, a, b, variante = preparar(api)
    assert registrar_movimiento(api, cabeceras, a, variante, 'entrada', 10).status_code == 201
    assert registrar_movimiento(api, cabeceras, a, variante, 'salida', 11).status_code == 409
    assert registrar_movimiento(api, cabeceras, a, variante, 'salida', 3).status_code == 201
    assert registrar_movimiento(api, cabeceras, a, variante, 'entrada', 0).status_code == 422
    assert api.get('/existencias', headers=cabeceras).json()[0]['cantidad'] == 7
    with SesionLocal() as base_datos:
        assert base_datos.scalar(select(func.sum(Movimiento.variacion_cantidad))) == 7
        assert base_datos.scalar(select(func.count()).select_from(Movimiento)) == 2


def test_recepcion_unica_y_reversion_de_envio_fallido(api):
    cabeceras, a, b, variante = preparar(api)
    registrar_movimiento(api, cabeceras, a, variante, 'entrada', 10)
    cuerpo = {'id_sucursal_origen': a, 'id_sucursal_destino': b, 'id_variante': variante, 'cantidad': 4}
    bad = api.post('/transferencias', headers=cabeceras, json={**cuerpo, 'cantidad': 11})
    assert bad.status_code == 409
    resultado = api.post('/transferencias', headers=cabeceras, json=cuerpo)
    assert resultado.status_code == 201, resultado.text
    id_transferencia = resultado.json()['id']
    assert api.get('/tablero', headers=cabeceras).json()['pares_en_transito'] == 4
    assert api.post(f'/transferencias/{id_transferencia}/recibir', headers=autenticar(api, 'operator_a', 'Operator-test-2026!')).status_code == 403
    receptor = autenticar(api, 'operator_b', 'Operator-test-2026!')
    assert api.post(f'/transferencias/{id_transferencia}/recibir', headers=receptor).status_code == 200
    assert api.post(f'/transferencias/{id_transferencia}/recibir', headers=receptor).status_code == 409
    with SesionLocal() as base_datos:
        assert base_datos.scalar(select(func.sum(Existencia.cantidad))) == 10
        assert base_datos.scalar(select(func.count()).select_from(Transferencia)) == 1
        assert base_datos.scalar(select(func.sum(Movimiento.variacion_cantidad))) == 10


def test_aprobacion_de_ajuste_y_existencias_minimas(api):
    cabeceras, a, b, variante = preparar(api)
    registrar_movimiento(api, cabeceras, a, variante, 'entrada', 10)
    operador = autenticar(api, 'operator_a', 'Operator-test-2026!')
    resultado = api.post('/ajustes', headers=operador, json={
        'id_sucursal': a, 'id_variante': variante, 'variacion_cantidad': -3, 'motivo': 'Diferencia en conteo físico'})
    id_ajuste = resultado.json()['id']
    ruta = f'/ajustes/{id_ajuste}/revisar'
    assert api.get('/existencias', headers=cabeceras).json()[0]['cantidad'] == 10
    assert api.post(ruta, headers=operador, json={'decision': 'aprobado'}).status_code == 403
    assert api.post(ruta, headers=cabeceras, json={'decision': 'aprobado'}).status_code == 200
    assert api.post(ruta, headers=cabeceras, json={'decision': 'aprobado'}).status_code == 409
    api.put(f'/existencias/{a}/{variante}/minimo', headers=cabeceras, json={'cantidad_minima': 8})
    assert api.get('/existencias?solo_bajo_minimo=true', headers=cabeceras).json()[0]['cantidad'] == 7
    tablero = api.get('/tablero', headers=cabeceras).json()
    assert Decimal(str(tablero['valor_estimado_inventario_bob'])) == Decimal('700.00')
    assert tablero['ajustes_pendientes'] == 0


def test_validacion_duplicados_y_cambio_de_contrasena(api):
    cabeceras, a, b, variante = preparar(api)
    assert api.post('/productos', headers=cabeceras, json={
        'codigo': 'MOD-001', 'nombre': 'Duplicado', 'categoria': 'Escolar'}).status_code == 409
    assert api.post('/transferencias', headers=cabeceras, json={
        'id_sucursal_origen': a, 'id_sucursal_destino': a, 'id_variante': variante, 'cantidad': 1}).status_code == 422
    assert api.patch('/usuarios/1/activo', headers=cabeceras, json={'activo': False}).status_code == 409
    assert api.post('/autenticacion/cambiar-contrasena', headers=cabeceras, json={
        'contrasena_actual': 'Administrador-test-2026!', 'contrasena_nueva': 'New-administrador-test-2026!'}).status_code == 200
    assert api.get('/autenticacion/mi-perfil', headers=cabeceras).status_code == 401
    assert autenticar(api, contrasena='New-administrador-test-2026!')
    assert api.get('/reconocimiento/estado', headers=autenticar(api, contrasena='New-administrador-test-2026!')).json()['disponible'] is True


def test_documentacion_y_datos_de_demostracion(api):
    from app.datos_demostracion import principal as datos_demostracion
    datos_demostracion()
    cabeceras = autenticar(api)
    assert api.get('/salud').json()['estado'] == 'correcto'
    assert api.get('/documentacion').status_code == 200
    assert '/transferencias/{id_transferencia}/recibir' in api.get('/esquema-api.json').json()['paths']
    assert len(api.get('/productos', headers=cabeceras).json()) == 5
    assert len(api.get('/variantes', headers=cabeceras).json()) == 15
    assert len(api.get('/existencias', headers=cabeceras).json()) == 30
    assert api.get('/tablero', headers=cabeceras).json()['pares_disponibles'] == 345
    with pytest.raises(RuntimeError):
        datos_demostracion()


def test_contrato_y_errores_en_espanol(api):
    cabeceras, a, b, variante = preparar(api)
    respuesta = api.post('/sucursales', headers=cabeceras, json={'name': 'Nombre antiguo'})
    assert respuesta.status_code == 422
    detalle = respuesta.json()['detalle']
    assert any(x['mensaje'] == 'Campo obligatorio' for x in detalle)
    assert any(x['mensaje'] == 'Campo no permitido' for x in detalle)
    assert all('input' not in x for x in detalle)
    assert api.get('/branches', headers=cabeceras).json() == {'detalle': 'Ruta no encontrada'}
    assert api.get('/reconocimiento/estado', headers=cabeceras).json()['estado'] == 'listo'
    contrato = api.get('/esquema-api.json').json()
    assert contrato['components']['schemas']['CrearUsuario']['properties']['rol']['enum'] == ['administrador', 'operador']
    assert set(contrato['components']['schemas']['Credenciales']['properties']) == {'nombre_usuario', 'contrasena'}
    assert 'Token_de_acceso' in contrato['components']['securitySchemes']


@pytest.mark.skipif(motor.dialect.name != 'postgresql', reason='Concurrencia verificada sobre PostgreSQL')
def test_salidas_simultaneas_sin_existencias_negativas(api):
    from concurrent.futures import ThreadPoolExecutor
    cabeceras, a, b, variante = preparar(api)
    registrar_movimiento(api, cabeceras, a, variante, 'entrada', 10)
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(lambda _: registrar_movimiento(api, cabeceras, a, variante, 'salida', 7).status_code, range(2)))
    assert sorted(resultados) == [201, 409]
    assert api.get('/existencias', headers=cabeceras).json()[0]['cantidad'] == 3


@pytest.mark.skipif(motor.dialect.name != 'postgresql', reason='Concurrencia verificada sobre PostgreSQL')
def test_recepciones_simultaneas_de_transferencia(api):
    from concurrent.futures import ThreadPoolExecutor
    cabeceras, a, b, variante = preparar(api)
    registrar_movimiento(api, cabeceras, a, variante, 'entrada', 10)
    id_transferencia = api.post('/transferencias', headers=cabeceras, json={
        'id_sucursal_origen': a, 'id_sucursal_destino': b, 'id_variante': variante, 'cantidad': 4}).json()['id']
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(lambda _: api.post(f'/transferencias/{id_transferencia}/recibir', headers=cabeceras).status_code, range(2)))
    assert sorted(resultados) == [200, 409]
    with SesionLocal() as base_datos:
        assert base_datos.scalar(select(func.sum(Existencia.cantidad))) == 10
        assert base_datos.scalar(select(func.count()).select_from(Movimiento).where(Movimiento.tipo == 'entrada_transferencia')) == 1
