"""Config for the provisional (v0) data-synthesis step — see config/import.json."""

from pydantic.dataclasses import dataclass

from core.config.modeles.commun import STRICT, Plage


@dataclass(frozen=True, slots=True, config=STRICT)
class SyntheseAttributsConfig:
    niveau: Plage
    marge_potentiel_defaut: float
    marge_potentiel_jeune_max: float
    marge_potentiel_age_seuil: int


@dataclass(frozen=True, slots=True, config=STRICT)
class SyntheseClubConfig:
    stad_cap_reference: Plage
    reputation: Plage
    reputation_bruit_ecart_type: float
    note_centre_formation: Plage
    note_centre_formation_facteur_reputation: float
    note_centre_formation_bruit_ecart_type: float


@dataclass(frozen=True, slots=True, config=STRICT)
class PostesImportConfig:
    affinite_secondaire_defaut: float


@dataclass(frozen=True, slots=True, config=STRICT)
class ConfigImport:
    synthese_attributs: SyntheseAttributsConfig
    synthese_club: SyntheseClubConfig
    postes: PostesImportConfig
