import atexit
import os
import tempfile
from pathlib import Path
import pytest

DIRECTORIO_PRUEBAS = tempfile.TemporaryDirectory(prefix='manaco-pruebas-')
url = os.environ.get('MANACO_URL_BD_PRUEBAS', 'sqlite:///' + str(Path(DIRECTORIO_PRUEBAS.name) / 'pruebas.db'))
if url.startswith('postgres') and not any(palabra in url.rsplit('/', 1)[-1].lower() for palabra in ('prueba', 'test')):
    raise RuntimeError('Las pruebas requieren una base exclusiva cuyo nombre incluya prueba o test.')
os.environ['URL_BASE_DATOS'] = url
os.environ['SECRETO_JWT'] = 'secreto-exclusivo-para-pruebas-1234567890'
os.environ['USUARIO_ADMINISTRADOR'] = 'administrador'
os.environ['CLAVE_ADMINISTRADOR'] = 'Administrador-test-2026!'

from fastapi.testclient import TestClient
from app.base_datos import Base, SesionLocal, motor
from app.inicializar_bd import principal as inicializar
from app.principal import app

atexit.register(motor.dispose)


@pytest.fixture
def api():
    Base.metadata.drop_all(motor)
    inicializar()
    with TestClient(app) as cliente:
        try:
            yield cliente
        finally:
            app.dependency_overrides.clear()
