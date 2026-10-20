# Modelo de categorías de calzado

Origen: `modelo_zapatos_final.zip`, aportado por el usuario. Se conserva el archivo Keras sin modificar ni volver a entrenar.

- Archivo: `modelo_zapatos.keras` (9,673,855 bytes).
- SHA-256: `f44fa96a9557c91a752d1cd8de352fffb3ac50d6e256dca701d9f8e6650e5f56`.
- Formato Keras 3, guardado con Keras 3.13.2. Base MobileNetV2 y salida softmax de tres clases.
- Entrada: RGB, 224 × 224 × 3, float32, píxeles 0..255.
- El modelo incluye Rescaling(1/127.5, offset=-1); no normalizar una segunda vez.
- Inferencia: `training=False`; carga con `compile=False` y `safe_mode=True`.

Orden de la salida, conservado desde `clases.json`:

| Posición | Clase | Código SA6 usado por la aplicación |
| --- | --- | --- |
| 0 | calzadoDeportivoSuelaPlastico | 640411 |
| 1 | calzadoSuelaCauchoSupCuero | 640399 |
| 2 | calzadoSuelaCueroSuperiorSimilar | 640420 |

Estos códigos vinculan las categorías del caso al catálogo; no identifican un producto ni certifican su material. El usuario confirma la categoría y la variante.

La carga y la inferencia se comprobaron técnicamente. No se entregaron datos de evaluación ni métricas verificables. Debe medirse la exactitud con fotografías reales independientes del entrenamiento. El modelo siempre distribuye sus puntuaciones entre estas tres clases y no incluye una clase desconocido.

El umbral 0.70 solo activa una advertencia de revisión. Toda predicción exige confirmación antes de registrar un movimiento. Las imágenes de consultas no se almacenan en el catálogo.
