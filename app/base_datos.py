from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .configuracion import obtener_configuracion


class Base(DeclarativeBase):
    pass


url = obtener_configuracion().url_base_datos
motor = create_engine(url, pool_pre_ping=True,
                       connect_args={'check_same_thread': False} if url.startswith('sqlite') else {})
if url.startswith('sqlite'):
    @event.listens_for(motor, 'connect')
    def claves_foraneas_sqlite(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')

SesionLocal = sessionmaker(bind=motor, expire_on_commit=False)


def obtener_bd():
    with SesionLocal() as base_datos:
        try:
            yield base_datos
        except Exception:
            base_datos.rollback()
            raise
