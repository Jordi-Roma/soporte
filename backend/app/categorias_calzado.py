import re
import unicodedata

CATEGORIAS = [
    {'codigo': 'calzadoDeportivoSuelaPlastico', 'nombre': 'Calzado deportivo con suela de caucho/plástico', 'codigo_sa6': '640411'},
    {'codigo': 'calzadoSuelaCauchoSupCuero', 'nombre': 'Calzado con suela de caucho/plástico y parte superior de cuero', 'codigo_sa6': '640399'},
    {'codigo': 'calzadoSuelaCueroSuperiorSimilar', 'nombre': 'Calzado con suela de cuero y parte superior de cuero/material similar', 'codigo_sa6': '640420'},
]


def normalizar_categoria(valor):
    texto = unicodedata.normalize('NFKD', str(valor)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', texto)


def coincide_categoria(valor, categoria):
    normalizado = normalizar_categoria(valor)
    return normalizado in {normalizar_categoria(categoria[clave]) for clave in ('codigo', 'nombre', 'codigo_sa6')}
