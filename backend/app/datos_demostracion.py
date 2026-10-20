"""Carga opcional de datos SIMULADOS. Nunca utiliza la base de comercio exterior."""
from sqlalchemy import select
from .base_datos import SesionLocal
from .modelos import Sucursal, Producto, Variante, Usuario
from .inventario import aplicar_movimiento, asegurar_existencia


def principal():
    with SesionLocal() as base_datos:
        if base_datos.scalar(select(Producto.id).limit(1)):
            raise RuntimeError('El catálogo no está vacío; se cancela la carga para evitar duplicados')
        administrador = base_datos.scalar(select(Usuario).where(Usuario.rol == 'administrador', Usuario.activo))
        if not administrador:
            raise RuntimeError('Ejecuta primero python -m app.inicializar_bd')
        sucursales = [Sucursal(nombre='DEMO Almacén central', direccion='Ubicación simulada'),
                    Sucursal(nombre='DEMO Sucursal centro', direccion='Ubicación simulada')]
        base_datos.add_all(sucursales)
        base_datos.flush()
        for index, nombre in enumerate(['Escolar A', 'Deportivo B', 'Casual C', 'Bota D', 'Sandalia E'], 1):
            producto = Producto(codigo=f'DEMO-{index:03}', nombre=nombre, categoria='Calzado de demostración',
                              descripcion='Producto ficticio para evaluación académica')
            base_datos.add(producto)
            base_datos.flush()
            for talla in ['38', '39', '40']:
                variante = Variante(id_producto=producto.id, codigo_variante=f'{producto.codigo}-{talla}-NEG', talla=talla,
                                  color='Negro', costo_referencia=100, precio_venta=180)
                base_datos.add(variante)
                base_datos.flush()
                for sucursal in sucursales:
                    asegurar_existencia(base_datos, sucursal.id, variante.id).cantidad_minima = 5
                    aplicar_movimiento(base_datos, sucursal.id, variante.id, 20 if sucursal == sucursales[0] else 3,
                                   'entrada', 'Existencia inicial SIMULADO', administrador.id)
        base_datos.commit()
    print('Datos SIMULADOS creados: 2 sucursales, 5 productos, 15 variantes y 30 entradas.')


if __name__ == '__main__':
    principal()
