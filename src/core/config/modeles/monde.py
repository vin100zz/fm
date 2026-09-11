from pydantic.dataclasses import dataclass

from core.config.modeles.commun import STRICT


@dataclass(frozen=True, slots=True, config=STRICT)
class CompetitionSimulee:
    pays: str
    nom: str
    niveau: int
    nb_clubs: int
    division_id: int
    nationalite_source: str


@dataclass(frozen=True, slots=True, config=STRICT)
class SaisonConfig:
    debut_mois: int
    debut_jour: int
    fin_mois: int
    fin_jour: int
    jours_entre_journees: int
    points_victoire: int
    points_nul: int
    points_defaite: int
    criteres_departage: list[str]


@dataclass(frozen=True, slots=True, config=STRICT)
class FenetreMercato:
    debut_mois: int
    debut_jour: int
    fin_mois: int
    fin_jour: int


@dataclass(frozen=True, slots=True, config=STRICT)
class MercatoConfig:
    ete: FenetreMercato
    hiver: FenetreMercato
    tours_par_jour: int


@dataclass(frozen=True, slots=True, config=STRICT)
class DateCle:
    mois: int
    jour: int


@dataclass(frozen=True, slots=True, config=STRICT)
class DatesClesConfig:
    promotion_centre_formation: DateCle
    liberation_contrats_expires: DateCle
    bilan_demographique: DateCle


@dataclass(frozen=True, slots=True, config=STRICT)
class ReglesMatchConfig:
    joueurs_sur_terrain: int
    remplacements_max: int
    fenetres_remplacement: int
    taille_banc: int


@dataclass(frozen=True, slots=True, config=STRICT)
class ConfigMonde:
    version_config: int
    competitions_simulees: list[CompetitionSimulee]
    saison: SaisonConfig
    mercato: MercatoConfig
    dates_cles: DatesClesConfig
    regles_match: ReglesMatchConfig
