from pydantic.dataclasses import dataclass

from core.config.modeles.commun import STRICT, PalierAge


@dataclass(frozen=True, slots=True, config=STRICT)
class ProgressionConfig:
    evaluation: str
    minutes_reference_par_mois: int
    facteur_jeu_min: float
    amplitude: float
    bruit_ecart_type: float
    courbe_age: list[PalierAge]
    poids_declin_par_attribut: dict[str, float]
    plafonne_par_potentiel: bool
    declin_plafonne: bool


@dataclass(frozen=True, slots=True, config=STRICT)
class EstimationPotentielConfig:
    bruit_max: float
    age_debut_convergence: int
    age_convergence: int
    facteur_reputation_observateur: float
    base_facteur_observateur: float


@dataclass(frozen=True, slots=True, config=STRICT)
class CohorteConfig:
    kappa_correction: float
    axes_correction: list[str]
    buckets_niveau: list[tuple[int, int]]


@dataclass(frozen=True, slots=True, config=STRICT)
class RatioNiveauSurPotentiel:
    age: int
    ratio: float


@dataclass(frozen=True, slots=True, config=STRICT)
class GenerationConfig:
    potentiel_min: int
    potentiel_amplitude: int
    beta_alpha_nation_moyenne: float
    beta_beta_nation_moyenne: float
    ratio_niveau_sur_potentiel: list[RatioNiveauSurPotentiel]
    bruit_niveau_ecart_type: float
    age_min: int
    age_max: int


@dataclass(frozen=True, slots=True, config=STRICT)
class CentresFormationConfig:
    promus_min: int
    promus_max: int
    moyenne_base: float
    poids_reputation: float
    poids_note_centre: float
    ecart_type_potentiel: float
    duree_contrat_annees: int
    salaire_hebdo_base: float


@dataclass(frozen=True, slots=True, config=STRICT)
class RetraiteConfig:
    age_minimal: int
    coefficient: float
    exposant: float
    facteur_niveau_base: float
    facteur_niveau_pente: float


@dataclass(frozen=True, slots=True, config=STRICT)
class SortiePerimetreConfig:
    age_minimal: int
    seuil_potentiel_estime: float
    sans_club_requis: bool


@dataclass(frozen=True, slots=True, config=STRICT)
class SortiesConfig:
    retraite: RetraiteConfig
    sortie_perimetre: SortiePerimetreConfig


@dataclass(frozen=True, slots=True, config=STRICT)
class ConfigDemographie:
    progression: ProgressionConfig
    estimation_potentiel: EstimationPotentielConfig
    cohorte: CohorteConfig
    cible_postes: dict[str, float]
    generation: GenerationConfig
    centres_formation: CentresFormationConfig
    sorties: SortiesConfig
