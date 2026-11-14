"""El 'hueco' de estrategias. Para añadir una nueva:
1. Crea un archivo aquí (p. ej. mi_estrategia.py) con una clase que herede de Estrategia.
2. Regístrala en ESTRATEGIAS (abajo).
3. Pon su nombre en config/intradia.yaml -> estrategia.nombre
"""
from .base import Estrategia
from .ejemplo_cruce_medias import CruceMedias
from .ninguna import Ninguna

ESTRATEGIAS: dict[str, type[Estrategia]] = {
    "ninguna": Ninguna,
    "ejemplo_cruce_medias": CruceMedias,
}


def crear(cfg_estrategia: dict) -> Estrategia:
    nombre = cfg_estrategia.get("nombre", "ninguna")
    if nombre not in ESTRATEGIAS:
        raise SystemExit(f"Estrategia '{nombre}' no existe. Opciones: {', '.join(ESTRATEGIAS)}")
    return ESTRATEGIAS[nombre](**(cfg_estrategia.get("parametros") or {}))
