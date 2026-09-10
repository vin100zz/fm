from pydantic.dataclasses import dataclass

from core.config.modeles.commun import STRICT, PalierAge


@dataclass(frozen=True, slots=True, config=STRICT)
class DecoteFinContrat:
    mois_max: int
    facteur: float


@dataclass(frozen=True, slots=True, config=STRICT)
class ValorisationConfig:
    base_euros: float
    exposant: float
    niveau_reference: float
    poids_potentiel_sur_niveau: float
    courbe_age: list[PalierAge]
    decote_fin_contrat: list[DecoteFinContrat]
    rarete_poste: dict[str, float]


@dataclass(frozen=True, slots=True, config=STRICT)
class UtiliteConfig:
    poids_preference_jeunes: float
    poids_appetit_risque: float
    age_seuil_jeunesse: int


@dataclass(frozen=True, slots=True, config=STRICT)
class EffectifParPoste:
    titulaires: int
    rotations: int
    doublures: int


@dataclass(frozen=True, slots=True, config=STRICT)
class ProfilCibleConfig:
    niveau_base: float
    poids_reputation: float
    decote_rotation: float
    decote_doublure: float
    effectif_par_poste: dict[str, EffectifParPoste]


@dataclass(frozen=True, slots=True, config=STRICT)
class RevenusConfig:
    base_par_point_reputation: float
    bonus_classement_premier: float
    decroissance_par_place: float
    multiplicateur_pays: dict[str, float]


@dataclass(frozen=True, slots=True, config=STRICT)
class BudgetsConfig:
    part_revenus_transfert: float
    part_solde_transfert: float
    part_revenus_salaires: float
    semaines_par_an: int
    revenus: RevenusConfig


@dataclass(frozen=True, slots=True, config=STRICT)
class ScoreJoueurConfig:
    poids_salaire: float
    poids_temps_de_jeu: float
    poids_reputation_club: float
    poids_ambition: float
    bruit_ecart_type: float


@dataclass(frozen=True, slots=True, config=STRICT)
class ClubsDormantsConfig:
    probabilite_acceptation_offre_au_prix: float
    multiplicateur_prix_demande: float
    probabilite_demarchage_par_fenetre: float
    part_cible_transferts_entrants: float


@dataclass(frozen=True, slots=True, config=STRICT)
class MercatoIAConfig:
    negociations_actives_max: int
    taille_shortlist: int
    seuil_vendeur_multiplicateur: float
    seuil_vendeur_reduction_surplus: float
    poids_patience_negociation: float
    ratio_contre_offre: float
    score_joueur: ScoreJoueurConfig
    clubs_dormants: ClubsDormantsConfig


@dataclass(frozen=True, slots=True, config=STRICT)
class DureeContratParAge:
    age_max: int
    annees: int


@dataclass(frozen=True, slots=True, config=STRICT)
class ContratsConfig:
    evaluation: str
    seuil_satisfaction_negociation: float
    mois_avant_fin_declenchant: int
    poids_salaire: float
    poids_temps_de_jeu: float
    poids_club: float
    facteur_ego: float
    duree_proposee_par_age: list[DureeContratParAge]


@dataclass(frozen=True, slots=True, config=STRICT)
class GardeFousConfig:
    effectif_min: int
    effectif_max: int
    gardiens_min: int
    gardiens_recommandes: int
    plafond_salarial_strict: bool
    solde_minimal_autorise: float


@dataclass(frozen=True, slots=True, config=STRICT)
class PlagePersonnalite:
    min: float
    max: float


@dataclass(frozen=True, slots=True, config=STRICT)
class PersonnaliteClubConfig:
    appetit_risque: PlagePersonnalite
    preference_jeunes: PlagePersonnalite
    agressivite_salariale: PlagePersonnalite
    patience_negociation: PlagePersonnalite
    correlation_reputation_agressivite: float


@dataclass(frozen=True, slots=True, config=STRICT)
class SelectionConfig:
    poids_composite: float
    poids_forme: float
    poids_fatigue: float
    seuil_rotation_fatigue: float
    ecart_niveau_acceptable_rotation: float


@dataclass(frozen=True, slots=True, config=STRICT)
class ConfigIA:
    valorisation: ValorisationConfig
    utilite: UtiliteConfig
    profil_cible: ProfilCibleConfig
    budgets: BudgetsConfig
    mercato: MercatoIAConfig
    contrats: ContratsConfig
    garde_fous: GardeFousConfig
    personnalite_club: PersonnaliteClubConfig
    selection: SelectionConfig
