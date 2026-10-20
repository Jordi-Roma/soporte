# Backend de inventario MANACO

Sistema académico de inventario por sucursal con Python, FastAPI y PostgreSQL. Las rutas, los campos JSON, los mensajes propios, los roles, los estados, las tablas, las columnas y los módulos del proyecto están en español. Las cantidades representan **pares** y los importes de referencia se expresan en **bolivianos (BOB)**.

Para conectar una interfaz, consultar [la guía del frontend](GUIA_FRONTEND.md). `contrato-api.json` contiene el contrato OpenAPI de esta versión. GitHub ejecutará las pruebas en PostgreSQL mediante el flujo incluido en `.github/workflows/pruebas.yml`.

## Estado de la base local

La base `manaco` contiene ocho tablas: `usuarios`, `sucursales`, `productos`, `variantes`, `existencias`, `movimientos`, `transferencias` y `ajustes`. Se conservó el administrador y los datos existentes al traducir los valores de roles y estados. El nombre de usuario local está en `USUARIO_ADMINISTRADOR` y la contraseña en `CLAVE_ADMINISTRADOR`, dentro de `.env`. No compartir ese archivo.

En pgAdmin: **manaco → Schemas → public → Tables**. Si la lista está desactualizada, usar Actualizar o reconectar.

## Iniciar en esta computadora

El backend ahora está dentro de `parcial soporte/backend`. Los comandos de esta guía se ejecutan desde `backend`; si la terminal está en la carpeta principal, ejecutar primero `cd backend`.

El entorno virtual ya está instalado. Desde esta carpeta en PowerShell:

```powershell
.\.venv\Scripts\python.exe -m app.inicializar_bd
.\.venv\Scripts\python.exe -m uvicorn app.principal:app --reload
```

La inicialización conserva los usuarios y tablas existentes. Abrir [documentación interactiva](http://127.0.0.1:8000/documentacion), [referencia de la API](http://127.0.0.1:8000/referencia) o [estado del servicio](http://127.0.0.1:8000/salud).

Si hay un servidor con la versión anterior en ejecución, detenerlo y volver a iniciarlo con `app.principal:app`.

## Preparación en otro equipo

```powershell
powershell -ExecutionPolicy Bypass -File .\preparar-local.ps1
```

Este archivo instala las versiones verificadas de `requirements.lock.txt` y genera claves aleatorias si no existe `.env`. No inicia servidores ni sobrescribe una configuración existente.

Configurar las siguientes variables en `.env`:

| Variable | Contenido |
| --- | --- |
| `URL_BASE_DATOS` | Conexión PostgreSQL con usuario, contraseña, servidor, puerto y base. |
| `SECRETO_JWT` | Secreto aleatorio de al menos 32 caracteres. |
| `MINUTOS_TOKEN` | Duración de la sesión; valor inicial 60 minutos. |
| `ORIGENES_CORS` | Arreglo JSON con las direcciones permitidas del frontend. |
| `USUARIO_ADMINISTRADOR` | Usuario que se crea al inicializar una base nueva. |
| `CLAVE_ADMINISTRADOR` | Contraseña inicial, mínimo 12 caracteres. |
| `CLAVE_BD` | Contraseña para la opción de PostgreSQL con Docker. |

Ejemplo de conexión: `postgresql+psycopg://postgres:CONTRASENA@localhost:5432/manaco`. Si la contraseña contiene caracteres reservados de URL, deben codificarse. El guion bajo es válido.

Con Docker Desktop, `docker compose up -d` crea PostgreSQL local en el puerto **5433**, usuario **manaco**, base **manaco**. En ese caso, ajustar `URL_BASE_DATOS` para que coincida con `CLAVE_BD`. El volumen conserva los datos. También se puede utilizar el PostgreSQL instalado en el equipo.

## Iniciar sesión y autorizar consultas

`POST /autenticacion/iniciar-sesion` recibe JSON:

```json
{
  "nombre_usuario": "admin",
  "contrasena": "TU_CONTRASENA_DEL_SISTEMA"
}
```

Usar los valores reales configurados en `.env`. El usuario `admin` es un ejemplo; las bases nuevas utilizan el valor de `USUARIO_ADMINISTRADOR`.

La respuesta contiene `token_acceso`, `tipo_token`, `expira_en_segundos` y `usuario`. En la documentación, copiar el valor de `token_acceso` en el control de autorización **Token_de_acceso**. El cliente envía después `Authorization: Bearer TOKEN`. Las palabras `Authorization`, `Bearer` y los métodos HTTP pertenecen al protocolo y conservan su forma estándar.

## Rutas disponibles

| Método | Ruta | Acción |
| --- | --- | --- |
| GET | `/salud` | Verificar conexión. |
| POST | `/autenticacion/iniciar-sesion` | Obtener una sesión. |
| GET | `/autenticacion/mi-perfil` | Consultar usuario autenticado. |
| POST | `/autenticacion/cerrar-sesion` | Revocar todas las sesiones del usuario. |
| POST | `/autenticacion/cambiar-contrasena` | Cambiar contraseña y revocar sesiones. |
| POST, GET | `/usuarios` | Crear y listar usuarios. |
| PATCH | `/usuarios/{id_usuario}/activo` | Activar o desactivar una cuenta. |
| POST, GET | `/sucursales` | Crear y listar sucursales. |
| POST, GET | `/productos` | Crear y buscar productos. |
| GET, PUT | `/productos/{id_producto}` | Consultar o actualizar un producto. |
| POST, GET | `/variantes` | Registrar y consultar tallas y colores. |
| GET | `/existencias` | Consultar inventario por sucursal. |
| PUT | `/existencias/{id_sucursal}/{id_variante}/minimo` | Configurar cantidad mínima. |
| POST, GET | `/movimientos` | Registrar y consultar entradas y salidas. |
| POST, GET | `/transferencias` | Enviar y consultar transferencias. |
| POST | `/transferencias/{id_transferencia}/recibir` | Confirmar recepción completa. |
| POST, GET | `/ajustes` | Solicitar y consultar correcciones. |
| POST | `/ajustes/{id_ajuste}/revisar` | Aprobar o rechazar un ajuste. |
| GET | `/tablero` | Consultar indicadores. |
| GET | `/reconocimiento/estado` | Consultar estado del modelo. |

Documentación: `/documentacion`, `/referencia` y contrato OpenAPI `/esquema-api.json`.

Los filtros son `id_sucursal`, `id_variante`, `id_producto`, `buscar`, `solo_bajo_minimo`, `desplazamiento` y `limite`, según la ruta. Las listas paginadas permiten un máximo de 200 registros por consulta.

## Ejemplos para el frontend

Crear sucursal:

```json
{"nombre": "Sucursal central", "direccion": "Dirección de demostración"}
```

Crear operador:

```json
{"nombre_usuario": "operador_centro", "nombre_completo": "Operador de demostración", "contrasena": "UnaClaveSegura2026!", "rol": "operador", "id_sucursal": 1}
```

Crear producto y variante:

```json
{"codigo": "MOD-001", "nombre": "Escolar A", "categoria": "Escolar", "descripcion": "Modelo de demostración", "url_foto": null}
```

```json
{"id_producto": 1, "codigo_variante": "MOD-001-38-NEG", "talla": "38", "color": "Negro", "costo_referencia": 100, "precio_venta": 180}
```

Registrar entrada o salida:

```json
{"id_sucursal": 1, "id_variante": 1, "tipo": "entrada", "cantidad": 10, "motivo": "Recepción de mercadería"}
```

Para una salida utilizar `"tipo": "salida"`. Crear transferencia:

```json
{"id_sucursal_origen": 1, "id_sucursal_destino": 2, "id_variante": 1, "cantidad": 4, "observacion": "Reposición de sucursal"}
```

Solicitar y revisar un ajuste:

```json
{"id_sucursal": 1, "id_variante": 1, "variacion_cantidad": -2, "motivo": "Diferencia en conteo físico"}
```

```json
{"decision": "aprobado"}
```

También se admite `"decision": "rechazado"`. Los errores propios se devuelven en `detalle`; los de validación contienen una lista con `ubicacion` y `mensaje`, sin repetir contraseñas ni otros valores recibidos.

## Permisos y reglas

- Roles: `administrador` y `operador`. El administrador gestiona usuarios, catálogo, mínimos y revisiones; el operador trabaja con su sucursal.
- El operador puede ver los destinos para preparar transferencias y el catálogo, pero no los costos ni precios.
- Las transferencias pasan de `en_transito` a `recibida`. Descuentan del origen al enviar y suman en el destino al confirmar; no se pueden recibir dos veces.
- Los ajustes pasan de `pendiente` a `aprobado` o `rechazado`. Solo la aprobación cambia las existencias.
- Tipos de movimiento: `entrada`, `salida`, `salida_transferencia`, `entrada_transferencia` y `ajuste`.
- No hay edición o eliminación de movimientos confirmados. Se corrigen mediante un ajuste con motivo y aprobación.
- Cada movimiento guarda responsable y fecha UTC. Las actualizaciones impiden existencias negativas incluso con solicitudes simultáneas.
- Las posiciones de inventario se crean al configurar un mínimo o registrar actividad. Para recibir alertas sobre una variante sin movimientos, configurar primero su mínimo.
- El tablero muestra pares disponibles, posiciones en mínimo o por debajo, pares en tránsito, ajustes pendientes y catálogo activo. El administrador ve además una valoración estimada con costos de referencia actuales; no equivale a utilidad ni a un estado financiero.

## Datos de demostración

```powershell
.\.venv\Scripts\python.exe -m app.datos_demostracion
```

Carga opcional de **datos simulados**: dos sucursales, cinco productos, quince variantes, treinta posiciones de existencias y sus entradas iniciales. Requiere catálogo vacío. No crea operadores ni utiliza el Excel de comercio exterior.

## Railway

1. Conectar el repositorio a un servicio Railway con la carpeta `/backend` como raíz y el archivo de configuración `/backend/railway.json`. El Dockerfile utiliza dependencias verificadas y ejecuta `app.inicializar_bd`, seguido de `app.principal:app`.
2. Añadir PostgreSQL. Configurar `URL_BASE_DATOS` con su conexión; por compatibilidad con Railway también se admite la variable estándar `DATABASE_URL`.
3. Configurar `SECRETO_JWT`, `USUARIO_ADMINISTRADOR`, `CLAVE_ADMINISTRADOR` y `ORIGENES_CORS` como arreglo JSON de direcciones exactas.
4. El control de salud utiliza `/salud`. La aplicación utiliza el puerto proporcionado por Railway. Generar el dominio público y consultar `/documentacion`.
5. Mantener una sola réplica y un solo proceso de API para este prototipo. El Dockerfile incluye el modelo y TensorFlow CPU. La memoria necesaria debe verificarse en el servicio real: cada proceso carga su propia copia del modelo. La primera predicción tarda más; `/salud` no carga el modelo. No se cargan datos de demostración automáticamente.
6. Publicar el frontend por HTTPS con `VITE_API_BASE_URL` apuntando a esta API, y añadir su origen exacto a `ORIGENES_CORS`. HTTPS permite utilizar la cámara. Probar una predicción después de desplegar; el servicio aún no se ha publicado ni verificado en Railway.

El servicio aún no se ha publicado. Si se actualiza una instalación que conserva roles y estados de la versión anterior, ejecutar una vez `python -m app.actualizar_idioma` antes de iniciar la nueva API. La actualización local ya fue realizada y conserva los registros; los usuarios deben volver a iniciar sesión.

## Pruebas y esquema

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Las pruebas utilizan una base SQLite temporal. Para incluir concurrencia en PostgreSQL, configurar `MANACO_URL_BD_PRUEBAS` con una **base exclusiva para pruebas**: las pruebas borran y reconstruyen sus tablas. Nunca utilizar la base principal para ello.

Las pruebas cubren permisos, sesiones, inventario, operaciones simultáneas, transferencias, ajustes, contrato de la API y reconocimiento. Para ejecutar también el archivo de modelo real, configurar `MANACO_PROBAR_MODELO_REAL=1`; sin esa variable se omite la prueba pesada. El procesamiento de imágenes, sus límites y la ausencia de movimientos automáticos se verifican siempre.

Comprobación local de la integración: **18 pruebas aprobadas en PostgreSQL 16**, incluida la carga e inferencia del modelo real. La prueba de la conexión desde el proxy del frontend también devolvió tres puntuaciones sin cambios de inventario. Se utilizaron imágenes sintéticas para validar el funcionamiento técnico, sin medir exactitud.

El archivo `esquema.sql` contiene el esquema físico generado desde los modelos en español. Los respaldos previos están en `respaldos/`, excluido de Git. Los cambios futuros de estructura requieren migraciones: `create_all` crea tablas faltantes y no modifica tablas existentes.

## Reconocimiento y límites del prototipo

El modelo aportado está incluido en `modelos_ia/`. La API ofrece, con sesión iniciada:

- `GET /reconocimiento/estado`: disponibilidad, categorías y límites.
- `GET /reconocimiento/categorias`: las tres categorías para los formularios del catálogo.
- `POST /reconocimiento/predecir`: archivo `imagen` mediante `multipart/form-data`; JPG, PNG o WebP, hasta 8 MB y 16 millones de píxeles por defecto.

La respuesta contiene `categoria_sugerida`, las tres `predicciones` con `puntuacion` entre 0 y 1, `confianza_baja`, `requiere_confirmacion` y `productos_sugeridos`. Analizar una foto no cambia las existencias. El usuario confirma producto, talla/color, sucursal, tipo y cantidad; solo después se llama a `POST /movimientos` con las mismas reglas de permisos y stock.

El modelo distingue categorías, no códigos de producto ni tallas. Las categorías del catálogo se pueden elegir al crear o editar productos. Se aceptan el nombre completo, el identificador de clase o su código SA6. Los valores anteriores, como Escolar, se conservan: deben asignarse manualmente a una categoría compatible si corresponde.

La imagen se orienta según EXIF, convierte a RGB y ajusta a 224 × 224. Los píxeles se entregan en 0..255 porque el modelo ya incluye su normalización. Se carga una sola vez por proceso al analizar la primera foto; esa primera solicitud tarda más. La ejecución usa CPU. `UMBRAL_RECONOCIMIENTO=0.70` es una regla de revisión, no una exactitud demostrada. Ver detalles y huella del archivo en `modelos_ia/README.md`.

No se recibió un conjunto de evaluación: falta medir la exactitud con fotografías reales ajenas al entrenamiento. El modelo siempre compara sus tres clases, incluso ante imágenes ajenas al calzado. Sus puntuaciones no prueban por sí solas que una identificación sea correcta.

La fotografía permanente del catálogo se guarda como URL HTTP/HTTPS. Las fotos enviadas al reconocimiento se procesan en memoria y no se incorporan al catálogo. No se incluyen facturación, compras completas, recuperación de contraseña por correo ni recepción parcial con discrepancias. La transferencia confirma un lote completo de una variante. El historial cubre movimientos y sus responsables; no todos los cambios del catálogo. Para operación pública sostenida, añadir límites de intentos de inicio de sesión, copias de seguridad y migraciones versionadas.
