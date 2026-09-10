from pydantic.dataclasses import dataclass

from core.config.modeles.commun import STRICT


@dataclass(frozen=True, slots=True, config=STRICT)
class IntensiteHauteurBloc:
    bloc_bas: float
    equilibre: float
    pressing_haut: float


@dataclass(frozen=True, slots=True, config=STRICT)
class FatigueConfig:
    consommation_par_minute: float
    resistance_base: float
    resistance_facteur_endurance: float
    intensite_par_hauteur_bloc: IntensiteHauteurBloc
    recuperation_base_par_jour: float
    recuperation_facteur_endurance: float
    facteur_age_jeune: float
    seuil_age_jeune: int
    facteur_age_vieux: float
    seuil_age_vieux: int
    seuil_alerte: float
    fatigue_retour_de_blessure: float


@dataclass(frozen=True, slots=True, config=STRICT)
class GraviteBlessure:
    nom: str
    part: float
    jours_min: int
    jours_max: int


@dataclass(frozen=True, slots=True, config=STRICT)
class PenalitePermanente:
    duree_minimale_jours: int
    age_minimal: int
    points_min: int
    points_max: int
    attributs_touches: list[str]


@dataclass(frozen=True, slots=True, config=STRICT)
class BlessuresConfig:
    probabilite_base_par_possession: float
    facteur_fatigue_max: float
    fragilite_min: float
    fragilite_max: float
    probabilite_quotidienne_hors_match: float
    gravites: list[GraviteBlessure]
    penalite_permanente: PenalitePermanente
    forme_retour_de_blessure: float


@dataclass(frozen=True, slots=True, config=STRICT)
class SeuilCumulJaunes:
    jaunes: int
    matches: int


@dataclass(frozen=True, slots=True, config=STRICT)
class SuspensionsConfig:
    matches_rouge_min: int
    matches_rouge_max: int
    matches_double_jaune: int
    seuils_cumul_jaunes: list[SeuilCumulJaunes]
    remise_a_zero_fin_saison: bool


@dataclass(frozen=True, slots=True, config=STRICT)
class FormeConfig:
    min: float
    max: float
    initiale: float
    note_reference: float
    sensibilite_note: float
    vitesse_convergence: float
    bruit_ecart_type: float


@dataclass(frozen=True, slots=True, config=STRICT)
class MoralConfig:
    min: float
    max: float
    initial: float
    amplitude_effet_match: float
    poids_temps_de_jeu: float
    poids_resultats_club: float
    poids_satisfaction_contrat: float
    vitesse_derive: float


@dataclass(frozen=True, slots=True, config=STRICT)
class RemplacementsConfig:
    premiere_minute_evaluation: int
    intervalle_evaluation_minutes: int
    seuil_fatigue_declenchement: float
    seuil_fatigue_joueur_averti: float
    ecart_niveau_acceptable_remplacant: float
    minutes_restantes_ajustement_tactique: int
    ecart_buts_ajustement_defensif: int


@dataclass(frozen=True, slots=True, config=STRICT)
class ConfigEtats:
    fatigue: FatigueConfig
    blessures: BlessuresConfig
    suspensions: SuspensionsConfig
    forme: FormeConfig
    moral: MoralConfig
    remplacements: RemplacementsConfig
