import importlib.util
import json
import logging
import os
import threading
import warnings
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from .categorias_calzado import CATEGORIAS
from .configuracion import obtener_configuracion

registro = logging.getLogger(__name__)


class ImagenNoValida(ValueError):
    pass


class ImagenDemasiadoGrande(ImagenNoValida):
    pass


class ModeloNoDisponible(RuntimeError):
    pass


def preparar_imagen(contenido, max_pixeles=16000000):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(contenido)) as imagen:
                if imagen.format not in {'JPEG', 'PNG', 'WEBP'}:
                    raise ImagenNoValida('Use una imagen JPG, PNG o WebP.')
                if imagen.width * imagen.height > max_pixeles:
                    raise ImagenDemasiadoGrande('La resolución de la imagen es demasiado grande. Reduzca su tamaño.')
                imagen = ImageOps.exif_transpose(imagen).convert('RGB')
                imagen = imagen.resize((224, 224), Image.Resampling.BILINEAR)
                # El modelo ya contiene Rescaling(1/127.5, offset=-1).
                # Se entregan píxeles 0..255, sin normalizar de nuevo.
                return np.asarray(imagen, dtype=np.float32)[np.newaxis, ...]
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ImagenDemasiadoGrande('La resolución de la imagen es demasiado grande.') from error
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        if isinstance(error, ImagenNoValida):
            raise
        raise ImagenNoValida('El archivo no contiene una imagen válida o está dañado.') from error


class ReconocedorCalzado:
    def __init__(self, directorio, umbral=0.7, max_pixeles=16000000):
        self.directorio = Path(directorio)
        self.umbral = umbral
        self.max_pixeles = max_pixeles
        self._modelo = None
        self._bloqueo = threading.RLock()
        self._ultimo_error = None

    def _clases(self):
        try:
            clases = json.loads((self.directorio / 'clases.json').read_text(encoding='utf-8'))
            if clases != [categoria['codigo'] for categoria in CATEGORIAS]:
                raise ValueError('Orden o clases inesperados')
            if not (self.directorio / 'modelo_zapatos.keras').is_file():
                raise FileNotFoundError('Falta el modelo')
            return clases
        except (OSError, ValueError, TypeError) as error:
            raise ModeloNoDisponible('No están disponibles el modelo y sus tres clases esperadas.') from error

    def estado(self):
        try:
            self._clases()
            dependencias = all(importlib.util.find_spec(nombre) is not None for nombre in ('keras', 'tensorflow'))
            disponible = dependencias and self._ultimo_error is None
            detalle = ('Modelo de tres categorías disponible. La primera predicción puede tardar más.' if disponible
                       else 'No se pudo preparar el modelo. Revise las dependencias y los registros del backend.')
        except ModeloNoDisponible as error:
            disponible = False
            detalle = str(error)
        return {'disponible': disponible, 'estado': 'listo' if disponible else 'no_disponible',
                'modelo_cargado': self._modelo is not None, 'detalle': detalle,
                'categorias': CATEGORIAS, 'entrada': {'ancho': 224, 'alto': 224, 'canales': 3},
                'umbral_sugerencia': self.umbral,
                'alcance': 'Clasifica categorías de calzado; el producto y su variante se confirman manualmente.'}

    def cargar(self):
        with self._bloqueo:
            if self._modelo is not None:
                return self._modelo
            self._clases()
            os.environ.setdefault('KERAS_BACKEND', 'tensorflow')
            os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
            os.environ.setdefault('TF_NUM_INTRAOP_THREADS', '2')
            os.environ.setdefault('TF_NUM_INTEROP_THREADS', '1')
            os.environ.setdefault('OMP_NUM_THREADS', '2')
            try:
                import keras
                modelo = keras.saving.load_model(self.directorio / 'modelo_zapatos.keras', compile=False, safe_mode=True)
                if tuple(modelo.input_shape[1:]) != (224, 224, 3) or modelo.output_shape[-1] != 3:
                    raise ValueError('Las dimensiones del modelo no coinciden con sus clases')
                self._modelo = modelo
                self._ultimo_error = None
                return modelo
            except Exception as error:
                self._ultimo_error = type(error).__name__
                registro.exception('No se pudo cargar el modelo de calzado')
                raise ModeloNoDisponible('No se pudo cargar el modelo. Revise la configuración del backend.') from error

    def predecir(self, contenido):
        lote = preparar_imagen(contenido, self.max_pixeles)
        with self._bloqueo:
            modelo = self.cargar()
            try:
                puntuaciones = np.asarray(modelo(lote, training=False), dtype=np.float32)
            except Exception as error:
                registro.exception('Falló la inferencia de calzado')
                raise ModeloNoDisponible('No se pudo procesar la imagen. Vuelva a intentar.') from error
        if (puntuaciones.shape != (1, 3) or not np.isfinite(puntuaciones).all()
                or np.any(puntuaciones < 0) or np.any(puntuaciones > 1)
                or not np.isclose(puntuaciones.sum(), 1, atol=0.001)):
            raise ModeloNoDisponible('El modelo devolvió una respuesta no válida.')
        predicciones = sorted([{**categoria, 'puntuacion': float(puntuaciones[0, indice])}
                               for indice, categoria in enumerate(CATEGORIAS)],
                              key=lambda categoria: categoria['puntuacion'], reverse=True)
        return {'categoria_sugerida': predicciones[0], 'predicciones': predicciones,
                'confianza_baja': predicciones[0]['puntuacion'] < self.umbral,
                'umbral_sugerencia': self.umbral, 'requiere_confirmacion': True,
                'detalle': 'Las puntuaciones no son una medida de exactitud. Confirme la categoría, el producto y la variante.'}


@lru_cache
def obtener_reconocedor():
    configuracion = obtener_configuracion()
    return ReconocedorCalzado(configuracion.directorio_modelo, configuracion.umbral_reconocimiento,
                             configuracion.max_pixeles_imagen)
