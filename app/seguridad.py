from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from .configuracion import obtener_configuracion
from .base_datos import obtener_bd
from .modelos import Usuario

gestor_claves = PasswordHash.recommended()
esquema_token = HTTPBearer(auto_error=False, scheme_name='Token_de_acceso',
                          description='Obtenga token_acceso al iniciar sesión y péguelo aquí.', bearerFormat='JWT')
HASH_FICTICIO = gestor_claves.hash('clave-ficticia-no-utilizada')


def crear_token(usuario: Usuario):
    configuracion = obtener_configuracion()
    return jwt.encode({'sub': str(usuario.id), 'ver': usuario.version_token,
                       'exp': datetime.now(timezone.utc) + timedelta(minutes=configuracion.minutos_token)},
                      configuracion.secreto_jwt, algorithm='HS256')


def usuario_actual(credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_token),
                   base_datos: Session = Depends(obtener_bd)):
    error = HTTPException(401, 'Sesión inválida o expirada', headers={'WWW-Authenticate': 'Bearer'})
    if credenciales is None:
        raise error
    try:
        datos = jwt.decode(credenciales.credentials, obtener_configuracion().secreto_jwt, algorithms=['HS256'],
                          options={'require': ['exp', 'sub', 'ver']})
        usuario = base_datos.get(Usuario, int(datos['sub']))
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise error
    if not usuario or not usuario.activo or usuario.version_token != datos['ver']:
        raise error
    return usuario


def administrador(usuario: Usuario = Depends(usuario_actual)):
    if usuario.rol != 'administrador':
        raise HTTPException(403, 'Se requiere rol administrador')
    return usuario


def acceso_sucursal(usuario: Usuario, id_sucursal: int):
    if usuario.rol != 'administrador' and usuario.id_sucursal != id_sucursal:
        raise HTTPException(403, 'No tiene permiso para esta sucursal')
