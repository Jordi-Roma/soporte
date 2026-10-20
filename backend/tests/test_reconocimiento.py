from io import BytesIO
import json
import os
from pathlib import Path
import numpy as np
from PIL import Image
import pytest
from app.principal import app
from app.categorias_calzado import CATEGORIAS, coincide_categoria
from app.reconocimiento import (ReconocedorCalzado, obtener_reconocedor, preparar_imagen,
                                ImagenNoValida, ModeloNoDisponible)


def imagen_png(color='white', tamano=(24, 24)):
    salida = BytesIO()
    Image.new('RGB', tamano, color).save(salida, format='PNG')
    return salida.getvalue()


def autenticar(api):
    respuesta = api.post('/autenticacion/iniciar-sesion', json={'nombre_usuario': 'administrador', 'contrasena': 'Administrador-test-2026!'})
    assert respuesta.status_code == 200
    return {'Authorization': 'Bearer ' + respuesta.json()['token_acceso']}


@pytest.fixture
def servicio():
    # Se sustituye solo la inferencia: se ejercitan la lectura y preparación reales de la imagen.
    reconocedor = ReconocedorCalzado(Path(__file__).resolve().parents[1] / 'modelos_ia')
    reconocedor._modelo = lambda lote, training=False: np.array([[0.8, 0.15, 0.05]], dtype=np.float32)
    app.dependency_overrides[obtener_reconocedor] = lambda: reconocedor
    yield reconocedor
    app.dependency_overrides.pop(obtener_reconocedor, None)


def test_preparacion_respeta_rgb_dimensiones_y_normalizacion_interna():
    lote = preparar_imagen(imagen_png())
    assert lote.shape == (1, 224, 224, 3)
    assert lote.dtype == np.float32
    assert np.all(lote == 255), 'El modelo recibe 0..255 y aplica su propia normalización'
    with pytest.raises(ImagenNoValida):
        preparar_imagen(b'archivo incorrecto')


def test_categoria_admite_codigo_nombre_y_sa6():
    categoria = CATEGORIAS[0]
    assert coincide_categoria(categoria['codigo'], categoria)
    assert coincide_categoria(categoria['nombre'].upper().replace('Á', 'A'), categoria)
    assert coincide_categoria('640411', categoria)
    assert not coincide_categoria('Escolar', categoria)


def test_prediccion_autenticada_sugiere_solo_productos_activos_y_no_modifica_stock(api, servicio):
    cabeceras = autenticar(api)
    def crear(codigo, categoria):
        respuesta = api.post('/productos', headers=cabeceras, json={'codigo': codigo, 'nombre': codigo, 'categoria': categoria})
        assert respuesta.status_code == 201
        return respuesta.json()['id']
    activo = crear('DEPORTIVO', CATEGORIAS[0]['nombre'])
    crear('OTRO', CATEGORIAS[1]['nombre'])
    inactivo = crear('INACTIVO', CATEGORIAS[0]['nombre'])
    api.put(f'/productos/{inactivo}', headers=cabeceras, json={'nombre': 'Inactivo', 'categoria': CATEGORIAS[0]['nombre'], 'activo': False})
    antes = api.get('/existencias', headers=cabeceras).json()
    respuesta = api.post('/reconocimiento/predecir', headers=cabeceras, files={'imagen': ('calzado.png', imagen_png(), 'image/png')})
    assert respuesta.status_code == 200, respuesta.text
    resultado = respuesta.json()
    assert resultado['categoria_sugerida']['codigo'] == CATEGORIAS[0]['codigo']
    assert len(resultado['predicciones']) == 3
    assert resultado['requiere_confirmacion'] is True
    assert [producto['id'] for producto in resultado['productos_sugeridos']] == [activo]
    assert api.get('/existencias', headers=cabeceras).json() == antes
    assert api.get('/movimientos', headers=cabeceras).json() == []


def test_prediccion_exige_sesion_e_imagen(api, servicio):
    assert api.post('/reconocimiento/predecir', files={'imagen': ('foto.png', imagen_png(), 'image/png')}).status_code == 401
    cabeceras = autenticar(api)
    respuesta = api.post('/reconocimiento/predecir', headers=cabeceras)
    assert respuesta.status_code == 422
    assert any('imagen' in error['ubicacion'] for error in respuesta.json()['detalle'])


def test_rechaza_archivos_invalidos_vacios_y_excesivos(api, servicio):
    cabeceras = autenticar(api)
    assert api.post('/reconocimiento/predecir', headers=cabeceras, files={'imagen': ('texto.txt', b'texto', 'text/plain')}).status_code == 415
    assert api.post('/reconocimiento/predecir', headers=cabeceras, files={'imagen': ('falso.png', b'texto', 'image/png')}).status_code == 400
    assert api.post('/reconocimiento/predecir', headers=cabeceras, files={'imagen': ('vacio.png', b'', 'image/png')}).status_code == 400
    assert api.post('/reconocimiento/predecir', headers=cabeceras, files={'imagen': ('grande.png', b'x' * (8 * 1024 * 1024 + 1), 'image/png')}).status_code == 413
    servicio.max_pixeles = 100
    assert api.post('/reconocimiento/predecir', headers=cabeceras, files={'imagen': ('resolucion.png', imagen_png(), 'image/png')}).status_code == 413


def test_puntuacion_baja_no_implica_registro_automatico(servicio):
    servicio._modelo = lambda lote, training=False: np.array([[0.34, 0.33, 0.33]], dtype=np.float32)
    resultado = servicio.predecir(imagen_png())
    assert resultado['confianza_baja'] is True
    assert resultado['requiere_confirmacion'] is True


def test_modelo_no_disponible_devuelve_error_claro(api, servicio):
    cabeceras = autenticar(api)
    def fallar(_):
        raise ModeloNoDisponible('No se pudo cargar el modelo.')
    servicio.predecir = fallar
    respuesta = api.post('/reconocimiento/predecir', headers=cabeceras, files={'imagen': ('foto.png', imagen_png(), 'image/png')})
    assert respuesta.status_code == 503
    assert respuesta.json()['detalle'] == 'No se pudo cargar el modelo.'


def test_estado_detecta_clases_desordenadas(tmp_path):
    (tmp_path / 'clases.json').write_text(json.dumps([categoria['codigo'] for categoria in reversed(CATEGORIAS)]))
    (tmp_path / 'modelo_zapatos.keras').write_bytes(b'marcador')
    assert ReconocedorCalzado(tmp_path).estado()['disponible'] is False


@pytest.mark.skipif(os.environ.get('MANACO_PROBAR_MODELO_REAL') != '1', reason='Activar para verificar el modelo real recibido')
def test_modelo_real_carga_y_predice_tres_categorias():
    servicio = ReconocedorCalzado(Path(__file__).resolve().parents[1] / 'modelos_ia')
    resultado = servicio.predecir(imagen_png())
    assert servicio.estado()['modelo_cargado'] is True
    assert len(resultado['predicciones']) == 3
    assert sum(item['puntuacion'] for item in resultado['predicciones']) == pytest.approx(1, abs=0.001)
