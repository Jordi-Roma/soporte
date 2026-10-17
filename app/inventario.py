from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from .modelos import Sucursal, Variante, Producto, Existencia, Movimiento


def requerir(base_datos, model, identificador):
    objeto = base_datos.get(model, identificador)
    if objeto is None:
        raise HTTPException(404, f'{model.__name__} no encontrado')
    return objeto


def validar_variante(base_datos, id_variante):
    variante = requerir(base_datos, Variante, id_variante)
    producto = requerir(base_datos, Producto, variante.id_producto)
    if not variante.activo or not producto.activo:
        raise HTTPException(409, 'Producto o variante inactiva')
    return variante


def asegurar_existencia(base_datos: Session, id_sucursal: int, id_variante: int):
    sucursal = requerir(base_datos, Sucursal, id_sucursal)
    if not sucursal.activo:
        raise HTTPException(409, 'Sucursal inactiva')
    validar_variante(base_datos, id_variante)
    # UPSERT evita dos filas de stock cuando llegan solicitudes simultáneas.
    dialect = base_datos.bind.dialect.name
    if dialect == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == 'sqlite':
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise RuntimeError('Base de datos no soportada')
    consulta = insert(Existencia).values(id_sucursal=id_sucursal, id_variante=id_variante, cantidad=0, cantidad_minima=0)
    base_datos.execute(consulta.on_conflict_do_nothing(index_elements=[Existencia.id_sucursal, Existencia.id_variante]))
    return base_datos.scalar(select(Existencia).where(Existencia.id_sucursal == id_sucursal, Existencia.id_variante == id_variante))


def aplicar_movimiento(base_datos, id_sucursal, id_variante, variacion_cantidad, tipo, motivo, id_usuario,
                   id_transferencia=None, id_ajuste=None):
    asegurar_existencia(base_datos, id_sucursal, id_variante)
    # Una sola sentencia comprueba y modifica stock: no permite sobreventa concurrente.
    resultado = base_datos.execute(update(Existencia).where(
        Existencia.id_sucursal == id_sucursal, Existencia.id_variante == id_variante,
        Existencia.cantidad + variacion_cantidad >= 0).values(cantidad=Existencia.cantidad + variacion_cantidad),
        execution_options={'synchronize_session': False})
    if resultado.rowcount != 1:
        raise HTTPException(409, 'Existencias insuficientes')
    movement = Movimiento(id_sucursal=id_sucursal, id_variante=id_variante, variacion_cantidad=variacion_cantidad,
                        tipo=tipo, motivo=motivo, id_usuario=id_usuario,
                        id_transferencia=id_transferencia, id_ajuste=id_ajuste)
    base_datos.add(movement)
    base_datos.flush()
    return movement
