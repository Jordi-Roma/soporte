"""Convierte roles y estados previos al español conservando los registros."""
from sqlalchemy import inspect, text
from .base_datos import motor


def principal():
    with motor.begin() as conexion:
        inspector = inspect(conexion)
        tablas = set(inspector.get_table_names())
        if not {'usuarios', 'transferencias', 'ajustes', 'movimientos'} <= tablas:
            raise RuntimeError('Falta el esquema de MANACO en español; ejecute primero app.inicializar_bd')
        for tabla, campo in [('usuarios', 'rol'), ('transferencias', 'estado'), ('ajustes', 'estado')]:
            for restriccion in inspector.get_check_constraints(tabla):
                if campo in restriccion['sqltext']:
                    nombre = motor.dialect.identifier_preparer.quote(restriccion['name'])
                    conexion.execute(text(f'ALTER TABLE {tabla} DROP CONSTRAINT {nombre}'))
        conexion.execute(text("UPDATE usuarios SET rol = CASE rol WHEN 'admin' THEN 'administrador' "
                              "WHEN 'operator' THEN 'operador' ELSE rol END, version_token = version_token + 1 "
                              "WHERE rol IN ('admin', 'operator')"))
        conexion.execute(text("UPDATE transferencias SET estado = CASE estado WHEN 'in_transit' THEN 'en_transito' "
                              "WHEN 'received' THEN 'recibida' ELSE estado END"))
        conexion.execute(text("UPDATE ajustes SET estado = CASE estado WHEN 'pending' THEN 'pendiente' "
                              "WHEN 'approved' THEN 'aprobado' WHEN 'rejected' THEN 'rechazado' ELSE estado END"))
        conexion.execute(text("UPDATE movimientos SET tipo = CASE tipo WHEN 'entry' THEN 'entrada' "
                              "WHEN 'exit' THEN 'salida' WHEN 'transfer_out' THEN 'salida_transferencia' "
                              "WHEN 'transfer_in' THEN 'entrada_transferencia' WHEN 'adjustment' THEN 'ajuste' ELSE tipo END"))
        conexion.execute(text("ALTER TABLE usuarios ADD CONSTRAINT ck_usuarios_rol "
                              "CHECK (rol IN ('administrador', 'operador'))"))
        conexion.execute(text("ALTER TABLE usuarios ADD CONSTRAINT ck_usuarios_sucursal_operador "
                              "CHECK (rol != 'operador' OR id_sucursal IS NOT NULL)"))
        conexion.execute(text("ALTER TABLE transferencias ADD CONSTRAINT ck_transferencias_estado "
                              "CHECK (estado IN ('en_transito', 'recibida'))"))
        conexion.execute(text("ALTER TABLE ajustes ADD CONSTRAINT ck_ajustes_estado "
                              "CHECK (estado IN ('pendiente', 'aprobado', 'rechazado'))"))
    print('Roles, estados y tipos de movimiento actualizados al español. Registros conservados.')


if __name__ == '__main__':
    principal()
