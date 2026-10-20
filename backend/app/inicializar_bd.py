from sqlalchemy import select
from .configuracion import obtener_configuracion
from .base_datos import Base, SesionLocal, motor
from .modelos import Usuario
from .seguridad import gestor_claves


def principal():
    Base.metadata.create_all(motor)
    configuracion = obtener_configuracion()
    with SesionLocal() as base_datos:
        if base_datos.scalar(select(Usuario).where(Usuario.rol == 'administrador', Usuario.activo)):
            print('Esquema inicial verificado; administrador existente.')
            return
        contrasena = configuracion.clave_administrador
        if not contrasena or len(contrasena) < 12 or 'REEMPLAZAR' in contrasena:
            raise RuntimeError('Configura CLAVE_ADMINISTRADOR (mínimo 12 caracteres) para crear el administrador inicial')
        base_datos.add(Usuario(nombre_usuario=configuracion.usuario_administrador, nombre_completo='Administrador MANACO', rol='administrador',
                    clave_hash=gestor_claves.hash(contrasena)))
        base_datos.commit()
    print('Esquema inicial y administrador creados. No se imprimen credenciales.')


if __name__ == '__main__':
    principal()
