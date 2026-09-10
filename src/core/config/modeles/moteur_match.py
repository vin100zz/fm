from pydantic.dataclasses import dataclass

from core.config.modeles.commun import STRICT


@dataclass(frozen=True, slots=True, config=STRICT)
class ChronologieConfig:
    duree_match_secondes: int
    duree_possession_moyenne: float
    duree_possession_forme_gamma: float
    temps_additionnel_min: int
    temps_additionnel_max: int
    secondes_par_arret_de_jeu: int


@dataclass(frozen=True, slots=True, config=STRICT)
class TransitionsConfig:
    k_prog: float
    k_occ: float
    bonus_domicile: float


@dataclass(frozen=True, slots=True, config=STRICT)
class DensiteConfig:
    reference: float
    exposant: float
    note_plancher: float


@dataclass(frozen=True, slots=True, config=STRICT)
class CouloirsMoteurConfig:
    beta_softmax: float
    probabilite_changement_aile: float
    poids_vision_changement_aile: float


@dataclass(frozen=True, slots=True, config=STRICT)
class OccasionConfig:
    xg_base_centre: float
    xg_base_frappe: float
    multiplicateur_contre: float
    sensibilite_tireur_gardien: float


@dataclass(frozen=True, slots=True, config=STRICT)
class CoupsArretesConfig:
    probabilite_corner_sur_turnover_avance: float
    probabilite_coup_franc_sur_turnover: float
    xg_base_corner: float
    xg_base_coup_franc_direct: float
    part_cible_buts_sur_cpa: float


@dataclass(frozen=True, slots=True, config=STRICT)
class TurnoverConfig:
    zone_declenchant_contre: str
    malus_defensif_contre: float
    malus_defensif_couloir_concerne: float
    duree_malus_possessions: int


@dataclass(frozen=True, slots=True, config=STRICT)
class CartonsConfig:
    probabilite_jaune_par_turnover_defensif: float
    probabilite_rouge_direct_par_turnover_defensif: float
    poids_zone_defense: float
    poids_agressivite_tacle: float


@dataclass(frozen=True, slots=True, config=STRICT)
class RecalculNotesConfig:
    palier_fatigue_minutes: int
    sur_remplacement: bool
    sur_carton_rouge: bool


@dataclass(frozen=True, slots=True, config=STRICT)
class AnalytiqueConfig:
    buts_attendus_base: float
    sensibilite_ecart_force: float
    bonus_domicile_buts: float
    buts_attendus_min: float


@dataclass(frozen=True, slots=True, config=STRICT)
class ConfigMoteur:
    chronologie: ChronologieConfig
    transitions: TransitionsConfig
    densite: DensiteConfig
    couloirs: CouloirsMoteurConfig
    occasion: OccasionConfig
    coups_arretes: CoupsArretesConfig
    turnover: TurnoverConfig
    cartons: CartonsConfig
    recalcul_notes: RecalculNotesConfig
    analytique: AnalytiqueConfig
