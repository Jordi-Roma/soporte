$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno de Python.' }
}
& '.venv/Scripts/python.exe' -m pip install -r requirements.lock.txt
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias.' }
& '.venv/Scripts/python.exe' -c @'
from pathlib import Path
import secrets
ruta = Path('.env')
if ruta.exists():
    print('Se conserva el archivo .env existente.')
else:
    clave_bd = secrets.token_urlsafe(24)
    clave_administrador = secrets.token_urlsafe(18)
    ruta.write_text(
        f'URL_BASE_DATOS=postgresql+psycopg://manaco:{clave_bd}@localhost:5433/manaco\n'
        f'CLAVE_BD={clave_bd}\n'
        f'SECRETO_JWT={secrets.token_urlsafe(48)}\n'
        'MINUTOS_TOKEN=60\n'
        'ORIGENES_CORS=["http://localhost:5173","http://localhost:3000"]\n'
        'USUARIO_ADMINISTRADOR=admin\n'
        f'CLAVE_ADMINISTRADOR={clave_administrador}\n', encoding='utf-8')
    print('Configuración local creada. Consulta CLAVE_ADMINISTRADOR dentro de .env; no compartas ese archivo.')
'@
if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar la configuración.' }
Write-Host 'Siguiente: docker compose up -d; luego python -m app.inicializar_bd usando el entorno virtual.'
