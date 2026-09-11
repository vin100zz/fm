"""Draw a new player — "Tirage d'un joueur" and "Centres de formation"
in docs/progression-demographie.md. Both regens (`generer_regen`) and
academy promotions (`promouvoir_centre_formation`) share the same
niveau/attributs/identité machinery via `_finaliser_joueur`; only how
the nation and potentiel are drawn differs.
"""

from random import Random

from core.config.modeles.demographie import RatioNiveauSurPotentiel
from core.config.modeles.racine import Config
from core.domain.club import Club
from core.domain.contrat import Contrat
from core.domain.date import Date
from core.domain.joueur import Joueur
from core.domain.poste import Poste
from core.world.demographie.identite import PoolsNoms, tirer_identite
from core.world.generation_attributs import generer_attributs_depuis_niveau


def nationalites_simulees(cfg: Config) -> frozenset[str]:
    return frozenset(competition.nationalite_source for competition in cfg.monde.competitions_simulees)


def tirer_nation(cfg: Config, rng: Random) -> str | None:
    """One of the 5 simulated nations (by production weight, itself
    prorated on `monde.competitions_simulees[].nb_clubs` rather than a
    separate duplicated table), or `None` for the abstract vivier
    extérieur — "le reste vient d'un vivier externe abstrait".
    """
    total_clubs = sum(competition.nb_clubs for competition in cfg.monde.competitions_simulees)
    poids_ligues = cfg.demographie.nations.poids_total_ligues_simulees

    tirage = rng.random()
    cumul = 0.0
    for competition in cfg.monde.competitions_simulees:
        cumul += poids_ligues * (competition.nb_clubs / total_clubs)
        if tirage < cumul:
            return competition.nationalite_source
    return None


def parametres_potentiel(nationalite: str | None, cfg: Config) -> tuple[float, float]:
    """"Une nation forte monte alpha, une nation faible monte beta" —
    reuses `ia_gestion.budgets.revenus.multiplicateur_pays` (already
    calibrated football-strength-by-country) instead of a new,
    independent per-nation parameter.
    """
    cfg_gen = cfg.demographie.generation
    competition = next(
        (c for c in cfg.monde.competitions_simulees if c.nationalite_source == nationalite), None
    )
    if competition is None:
        return cfg_gen.beta_alpha_nation_moyenne, cfg_gen.beta_beta_nation_moyenne

    multiplicateur = cfg.ia.budgets.revenus.multiplicateur_pays.get(competition.pays, 1.0)
    exposant = cfg.demographie.nations.exposant_force_nation
    return (
        cfg_gen.beta_alpha_nation_moyenne * multiplicateur**exposant,
        cfg_gen.beta_beta_nation_moyenne / multiplicateur**exposant,
    )


def tirer_potentiel(alpha: float, beta: float, cfg: Config, rng: Random) -> int:
    cfg_gen = cfg.demographie.generation
    return round(cfg_gen.potentiel_min + cfg_gen.potentiel_amplitude * rng.betavariate(alpha, beta))


def tirer_poste(cfg: Config, rng: Random, poids: dict[str, float] | None = None) -> Poste:
    poids = poids or cfg.demographie.cible_postes
    total = sum(poids.values())
    tirage = rng.random() * total
    cumul = 0.0
    for code, part in poids.items():
        cumul += part
        if tirage < cumul:
            return Poste(code)
    return Poste(list(poids)[-1])  # filet de securite si l'arrondi flottant deborde


def tirer_age(cfg: Config, rng: Random) -> int:
    cfg_gen = cfg.demographie.generation
    return rng.randint(cfg_gen.age_min, cfg_gen.age_max)


def tirer_niveau_actuel(potentiel: int, age: int, cfg: Config, rng: Random) -> float:
    cfg_gen = cfg.demographie.generation
    ratio = _interpoler_ratio(age, cfg_gen.ratio_niveau_sur_potentiel)
    return potentiel * ratio * rng.gauss(1.0, cfg_gen.bruit_niveau_ecart_type)


def _interpoler_ratio(age: int, table: list[RatioNiveauSurPotentiel]) -> float:
    points = sorted(table, key=lambda point: point.age)
    if age <= points[0].age:
        return points[0].ratio
    if age >= points[-1].age:
        return points[-1].ratio
    for debut, fin in zip(points, points[1:]):
        if debut.age <= age <= fin.age:
            portion = (age - debut.age) / (fin.age - debut.age)
            return debut.ratio + portion * (fin.ratio - debut.ratio)
    return points[-1].ratio  # inatteignable, filet de securite


def generer_regen(
    id: int,
    club_id: int | None,
    date_actuelle: Date,
    pools: PoolsNoms,
    deja_utilises: frozenset[tuple[str, str]],
    cfg: Config,
    rng: Random,
    poids_poste: dict[str, float] | None = None,
) -> Joueur:
    age = tirer_age(cfg, rng)
    nationalite_cible = tirer_nation(cfg, rng)
    alpha, beta = parametres_potentiel(nationalite_cible, cfg)
    potentiel = tirer_potentiel(alpha, beta, cfg, rng)
    poste = tirer_poste(cfg, rng, poids_poste)
    return _finaliser_joueur(id, club_id, age, potentiel, poste, nationalite_cible, date_actuelle, pools, deja_utilises, cfg, rng)


def promouvoir_centre_formation(
    club: Club,
    premier_id: int,
    date_actuelle: Date,
    pools: PoolsNoms,
    deja_utilises: frozenset[tuple[str, str]],
    cfg: Config,
    rng: Random,
) -> list[Joueur]:
    """"Mettre beaucoup de variance et des queues épaisses" — potentiel
    tiré normalement (pas via la loi bêta du tirage général) autour
    d'une moyenne dérivée de la réputation du club et de son centre de
    formation, avec un grand écart-type pour permettre un joyau
    ponctuel même dans un petit club.
    """
    cfg_cf = cfg.demographie.centres_formation
    cfg_gen = cfg.demographie.generation
    potentiel_max = cfg_gen.potentiel_min + cfg_gen.potentiel_amplitude
    moyenne = cfg_cf.moyenne_base + cfg_cf.poids_reputation * club.reputation + cfg_cf.poids_note_centre * club.note_centre_formation
    date_fin_contrat = Date(date_actuelle.annee + cfg_cf.duree_contrat_annees, date_actuelle.mois, date_actuelle.jour)

    promus: list[Joueur] = []
    utilises = deja_utilises
    for i in range(rng.randint(cfg_cf.promus_min, cfg_cf.promus_max)):
        potentiel = round(min(max(rng.gauss(moyenne, cfg_cf.ecart_type_potentiel), cfg_gen.potentiel_min), potentiel_max))
        age = tirer_age(cfg, rng)
        nationalite_cible = tirer_nation(cfg, rng)
        poste = tirer_poste(cfg, rng)

        joueur = _finaliser_joueur(
            premier_id + i, club.id, age, potentiel, poste, nationalite_cible, date_actuelle, pools, utilises, cfg, rng
        )
        joueur.contrat = Contrat(
            salaire_hebdo=round(cfg_cf.salaire_hebdo_base), date_fin=date_fin_contrat, date_signature=date_actuelle
        )
        promus.append(joueur)
        utilises = utilises | {(joueur.nom, joueur.prenom)}
    return promus


def _finaliser_joueur(
    id: int,
    club_id: int | None,
    age: int,
    potentiel: int,
    poste: Poste,
    nationalite_cible: str | None,
    date_actuelle: Date,
    pools: PoolsNoms,
    deja_utilises: frozenset[tuple[str, str]],
    cfg: Config,
    rng: Random,
) -> Joueur:
    niveau = tirer_niveau_actuel(potentiel, age, cfg, rng)
    attributs = generer_attributs_depuis_niveau(niveau, poste, cfg.attributs, rng)
    nationalite, nom, prenom = tirer_identite(
        nationalite_cible, pools, deja_utilises, rng, cfg.demographie.identite.tentatives_max_unicite
    )
    date_naissance = Date(date_actuelle.annee - age, date_actuelle.mois, date_actuelle.jour)

    return Joueur(
        id=id, nom=nom, prenom=prenom, nationalite=nationalite, date_naissance=date_naissance,
        poste=poste, attributs=attributs, potentiel=potentiel,
        forme=cfg.etats.forme.initiale, fatigue=cfg.etats.fatigue.initiale, moral=cfg.etats.moral.initial,
        fragilite=rng.uniform(cfg.etats.blessures.fragilite_min, cfg.etats.blessures.fragilite_max),
        club_id=club_id, contrat=None,
    )
