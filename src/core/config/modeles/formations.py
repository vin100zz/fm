from pydantic.dataclasses import dataclass

from core.config.modeles.commun import STRICT


@dataclass(frozen=True, slots=True, config=STRICT)
class HauteurBlocConfig:
    min: float
    max: float
    defaut: float
    bonus_zone_recuperation: float
    malus_vulnerabilite_contre: float
    ajustement_menes_fin_match: float
    malus_inferiorite_numerique: float


@dataclass(frozen=True, slots=True, config=STRICT)
class ConfigFormations:
    formations: dict[str, list[str]]
    hauteur_bloc: HauteurBlocConfig
