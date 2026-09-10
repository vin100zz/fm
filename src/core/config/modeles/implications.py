from pydantic.dataclasses import dataclass

from core.config.modeles.commun import STRICT


@dataclass(frozen=True, slots=True, config=STRICT)
class ConfigImplications:
    zones: list[str]
    couloirs: list[str]
    vertical_attaque: dict[str, list[float]]
    vertical_defense: dict[str, list[float]]
    lateral: dict[str, list[float]]
