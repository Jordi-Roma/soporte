# Conectar el frontend de MANACO

Este repositorio contiene el backend. El frontend puede estar en otro repositorio y consumir esta API desde una dirección configurable. No necesita credenciales de PostgreSQL ni acceso directo a la base de datos.

## Preparar la conexión

1. Seguir el README para iniciar un backend local propio o utilizar la dirección del backend cuando esté publicado en Railway.
2. Configurar la dirección base en el frontend. Ejemplos: `http://127.0.0.1:8000` para el backend ejecutado en la misma computadora, o el dominio de Railway. La dirección `localhost` de una computadora no apunta a la computadora del compañero.
3. Incluir la dirección del frontend en `ORIGENES_CORS` del backend. Por defecto se permiten `http://localhost:5173` y `http://localhost:3000`. Si el frontend se abre con `127.0.0.1`, incluir también ese origen exacto. Reiniciar el backend después de cambiar su configuración.
4. Consultar `/documentacion` para probar peticiones o importar `contrato-api.json` en una herramienta compatible con OpenAPI. El contrato incluye rutas, cuerpos de entrada y autenticación; algunos resultados se documentan mediante los ejemplos de esta guía y del README.

## Login y permisos

Enviar JSON a `POST /autenticacion/iniciar-sesion`:

```json
{"nombre_usuario": "TU_USUARIO", "contrasena": "TU_CONTRASENA"}
```

La respuesta tiene esta estructura:

```json
{
  "token_acceso": "TOKEN_JWT",
  "tipo_token": "bearer",
  "expira_en_segundos": 3600,
  "usuario": {
    "id": 1,
    "nombre_usuario": "TU_USUARIO",
    "nombre_completo": "Nombre del usuario",
    "rol": "administrador",
    "id_sucursal": null,
    "activo": true
  }
}
```

Las siguientes peticiones llevan `Authorization: Bearer TOKEN_JWT`. Los cuerpos JSON llevan `Content-Type: application/json`. `GET /autenticacion/mi-perfil` permite consultar la sesión actual. Un error 401 requiere volver al inicio de sesión. Al cerrar sesión se revocan todas las sesiones del usuario.

Roles: `administrador` y `operador`. El frontend muestra las acciones que corresponden al rol; el backend también verifica los permisos. El administrador crea las cuentas con `POST /usuarios`; no hay registro público. Cada operador necesita `id_sucursal`.

## Pantallas y acciones disponibles

| Pantalla | Consultar | Acciones |
| --- | --- | --- |
| Inicio | `GET /tablero` | Mostrar indicadores. |
| Sucursales | `GET /sucursales` | `POST /sucursales`: crear, solo administrador. |
| Usuarios | `GET /usuarios` | `POST /usuarios`: crear; `PATCH /usuarios/{id_usuario}/activo`: activar o desactivar, solo administrador. |
| Productos | `GET /productos`, `GET /productos/{id_producto}` | `POST /productos`: crear; `PUT /productos/{id_producto}`: actualizar, solo administrador. |
| Variantes | `GET /variantes?id_producto=1` | `POST /variantes`: crear talla/color, solo administrador. |
| Inventario | `GET /existencias` | `PUT /existencias/{id_sucursal}/{id_variante}/minimo`: configurar mínimo, solo administrador. |
| Movimientos | `GET /movimientos` | `POST /movimientos`: registrar entrada o salida. |
| Transferencias | `GET /transferencias` | `POST /transferencias`: enviar; `POST /transferencias/{id_transferencia}/recibir`: recibir. |
| Ajustes | `GET /ajustes` | `POST /ajustes`: solicitar; `POST /ajustes/{id_ajuste}/revisar`: revisar, solo administrador. |
| Reconocimiento | `GET /reconocimiento/estado` | Mostrar que está pendiente de entrenamiento. |

Crear una sucursal recibe `nombre` y `direccion`. La respuesta incluye `id`, `nombre`, `direccion` y `activo`. Los ejemplos de productos, usuarios, variantes y movimientos están en el README.

Los formularios deben respetar las acciones disponibles. Por ejemplo, no hay endpoints para editar sucursales, borrar movimientos, recuperar contraseñas por correo ni cargar fotografías como archivos. La foto del producto se registra mediante `url_foto`.

## Listas, cantidades y errores

- Las listas son arreglos JSON. Las listas paginadas aceptan `desplazamiento` y `limite`, con un máximo de 200 elementos. Las sucursales se devuelven como lista completa.
- Productos admite `buscar`. Variantes admite `id_producto`. Existencias admite `id_sucursal` y `solo_bajo_minimo`. Movimientos admite `id_sucursal` e `id_variante`. Tablero admite `id_sucursal`.
- Las cantidades son enteros y representan pares. Una variante distingue modelo, talla y color. Los costos y precios son importes en BOB.
- Las fechas se devuelven en formato ISO y se guardan en UTC.
- El operador solo consulta y modifica inventario de su sucursal. Puede ver las sucursales de destino, pero no costos ni precios.
- Los errores 400/401/403/404/409 tienen `detalle` como texto. El 422 contiene una lista en `detalle`, con `ubicacion` y `mensaje` por error.

Valores permitidos: movimientos `entrada` y `salida`; transferencias `en_transito` y `recibida`; ajustes `pendiente`, `aprobado` y `rechazado`. Para revisar un ajuste se envía `{"decision":"aprobado"}` o `{"decision":"rechazado"}`.

Antes de registrar un movimiento, confirmar producto, variante y cantidad. El reconocimiento visual todavía no está disponible; la selección de productos es manual.
