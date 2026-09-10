from pydantic.dataclasses import dataclass

from core.config.modeles.commun import STRICT


@dataclass(frozen=True, slots=True, config=STRICT)
class ListeAttributs:
    techniques: list[str]
    mentaux: list[str]
    physiques: list[str]
    gardien: list[str]


@dataclass(frozen=True, slots=True, config=STRICT)
class BornesAttributs:
    min: int
    max: int


@dataclass(frozen=True, slots=True, config=STRICT)
class MalusHorsPoste:
    base: float
    facteur: float


@dataclass(frozen=True, slots=True, config=STRICT)
class ProfilsGeneration:
    bruit_ecart_type: float
    profils: dict[str, dict[str, float]]


@dataclass(frozen=True, slots=True, config=STRICT)
class ConfigAttributs:
    liste: ListeAttributs
    bornes: BornesAttributs
    composites: dict[str, dict[str, float]]
    note_globale: dict[str, dict[str, float]]
    profils_generation: ProfilsGeneration
    malus_hors_poste: MalusHorsPoste
