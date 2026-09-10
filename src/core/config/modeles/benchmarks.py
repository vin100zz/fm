from pydantic.dataclasses import dataclass

from core.config.modeles.commun import STRICT, CibleTolerance, Plage


@dataclass(frozen=True, slots=True, config=STRICT)
class ExecutionConfig:
    iterations_defaut_match: int
    iterations_defaut_saison: int
    saisons_demographie: int
    saisons_economie: int
    graine_defaut: int
    parallelisme: str


@dataclass(frozen=True, slots=True, config=STRICT)
class AffrontementReference:
    id: str
    domicile: str
    exterieur: str
    victoire: float
    nul: float
    defaite: float
    tolerance: list[float]


@dataclass(frozen=True, slots=True, config=STRICT)
class DistributionScoresConfig:
    score_le_plus_frequent: list[str]
    part_matches_zero_but: Plage
    part_matches_quatre_buts_ou_plus: Plage
    ecart_buts_moyen: Plage


@dataclass(frozen=True, slots=True, config=STRICT)
class StatsMatchConfig:
    possessions_par_equipe: Plage
    tirs_par_equipe: Plage
    xg_par_equipe: Plage
    buts_par_equipe: CibleTolerance
    possession_pct: Plage
    avantage_domicile_buts: CibleTolerance
    part_buts_coups_arretes: Plage
    jaunes_par_equipe: Plage
    rouges_par_equipe: Plage
    repartition_couloirs: CibleTolerance
    xg_axe_superieur_aile: bool


@dataclass(frozen=True, slots=True, config=STRICT)
class SaisonBenchmarkConfig:
    points_champion: Plage
    points_dernier: Plage
    ecart_type_points: Plage
    buts_meilleur_buteur: Plage
    titres_club_le_plus_fort_sur_100: Plage
    correlation_reputation_classement: Plage


@dataclass(frozen=True, slots=True, config=STRICT)
class FormationsBenchmarkConfig:
    taux_victoire_max_contre_le_champ: float
    taux_victoire_min_contre_le_champ: float
    levier_correction: str


@dataclass(frozen=True, slots=True, config=STRICT)
class OracleConfig:
    ecart_max_taux: float


@dataclass(frozen=True, slots=True, config=STRICT)
class DemographieBenchmarkConfig:
    derive_effectif_total: float
    derive_parts_postes: float
    derive_parts_nations: float
    derive_joueurs_au_dessus_85: float
    age_moyen_effectifs: Plage


@dataclass(frozen=True, slots=True, config=STRICT)
class SeuilMax:
    max: float


@dataclass(frozen=True, slots=True, config=STRICT)
class SeuilMin:
    min: float


@dataclass(frozen=True, slots=True, config=STRICT)
class EconomieBenchmarkConfig:
    part_max_joueurs_80_dans_top3: float
    transferts_par_club_fenetre_ete: Plage
    champions_differents_par_pays_sur_25: SeuilMin
    clubs_solde_negatif_permanent: SeuilMax
    part_transferts_depuis_dormants: Plage
    derive_masse_salariale_annuelle_max: float


@dataclass(frozen=True, slots=True, config=STRICT)
class PerformanceBenchmarkConfig:
    ms_par_match_possession: float
    secondes_par_saison_complete: float
    secondes_100_saisons_analytique: float
    secondes_chargement_donnees: float
    secondes_sauvegarde: float


@dataclass(frozen=True, slots=True, config=STRICT)
class ConfigBenchmarks:
    execution: ExecutionConfig
    affrontements_reference: list[AffrontementReference]
    distribution_scores: DistributionScoresConfig
    stats_match: StatsMatchConfig
    saison: SaisonBenchmarkConfig
    formations: FormationsBenchmarkConfig
    oracle: OracleConfig
    demographie: DemographieBenchmarkConfig
    economie: EconomieBenchmarkConfig
    performance: PerformanceBenchmarkConfig
    ordre_calibrage: list[str]
