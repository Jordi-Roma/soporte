# Proyecto MANACO

El backend está en la carpeta [backend](backend/README.md). Incluye la API en español, el esquema de PostgreSQL, las pruebas y la configuración para Railway.

```text
parcial soporte/
├── backend/
│   ├── app/
│   ├── tests/
│   ├── README.md
│   ├── GUIA_FRONTEND.md
│   ├── contrato-api.json
│   ├── esquema.sql
│   ├── Dockerfile
│   └── railway.json
└── .github/workflows/pruebas.yml
```

## Iniciar el backend

Desde esta carpeta, en PowerShell:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.principal:app --reload
```

En otra computadora, preparar primero el entorno siguiendo el [README del backend](backend/README.md). La configuración privada está en `backend/.env`; no se sube a Git.

La documentación estará en [http://127.0.0.1:8000/documentacion](http://127.0.0.1:8000/documentacion).

## Frontend

Consultar [la guía de integración](backend/GUIA_FRONTEND.md) y el [contrato de la API](backend/contrato-api.json). El frontend puede añadirse en otra carpeta del proyecto.

## Railway

Configurar la raíz del servicio como `/backend` y, si se especifica la ruta del archivo de configuración, usar `/backend/railway.json`. Los comandos de inicio se ejecutan desde esa carpeta. Las variables de PostgreSQL y autenticación se describen en el [README del backend](backend/README.md).

El repositorio Git y las pruebas de GitHub Actions permanecen en la carpeta principal. El flujo ejecuta las pruebas dentro de `backend`.
