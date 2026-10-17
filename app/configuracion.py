from functools import lru_cache
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    url_base_datos: str = Field(validation_alias=AliasChoices('URL_BASE_DATOS', 'DATABASE_URL'))
    secreto_jwt: str = Field(min_length=32)
    minutos_token: int = Field(default=60, ge=1, le=1440)
    origenes_cors: list[str] = ['http://localhost:5173']
    usuario_administrador: str = 'administrador'
    clave_administrador: str | None = None

    @field_validator('secreto_jwt')
    @classmethod
    def secreto_real(cls, value):
        if 'REEMPLAZAR' in value:
            raise ValueError('Configura SECRETO_JWT con un secreto aleatorio real')
        return value

    @field_validator('url_base_datos')
    @classmethod
    def controlador_postgres(cls, value):
        for prefix in ('postgres://', 'postgresql://'):
            if value.startswith(prefix):
                return value.replace(prefix, 'postgresql+psycopg://', 1)
        return value


@lru_cache
def obtener_configuracion():
    return Configuracion()
