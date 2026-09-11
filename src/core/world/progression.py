"""Monthly progression and decline. See "Progression et déclin" in
docs/progression-demographie.md.
"""

from random import Random

from core.config.modeles.commun import PalierAge
from core.config.modeles.racine import Config
from core.domain.attributs import NOMS_ATTRIBUTS
from core.domain.date import Date
from core.domain.joueur import Joueur
from core.world.note_globale import note_globale


def facteur_par_age(age: float, paliers: list[PalierAge]) -> float:
    """Linear interpolation between palier midpoints ("Interpoler
    linéairement entre les paliers" — docs/ia-gestion.md), clamped to the
    first/last palier's factor outside the range they cover.
    """
    paliers_tries = sorted(paliers, key=lambda palier: palier.age_min)
    milieux = [(palier.age_min + palier.age_max) / 2 for palier in paliers_tries]

    if age <= milieux[0]:
        return paliers_tries[0].facteur
    if age >= milieux[-1]:
        return paliers_tries[-1].facteur

    for i in range(len(paliers_tries) - 1):
        if milieux[i] <= age <= milieux[i + 1]:
            portion = (age - milieux[i]) / (milieux[i + 1] - milieux[i])
            return paliers_tries[i].facteur + portion * (paliers_tries[i + 1].facteur - paliers_tries[i].facteur)
    return paliers_tries[-1].facteur  # unreachable, kept as a safety net


def progresser(joueur: Joueur, minutes_mois: float, date_actuelle: Date, rng: Random, cfg: Config) -> None:
    """Mutates joueur.attributs in place — see "Progression et déclin" in
    docs/progression-demographie.md. Growth is spread evenly across every
    attribute (adding the same delta everywhere raises note_globale by
    exactly that delta, since its weights sum to 1.0) and capped by
    potentiel; decline is reweighted per attribute
    (poids_declin_par_attribut) and never capped.
    """
    cfg_prog = cfg.demographie.progression
    age = joueur.date_naissance.age_a(date_actuelle)
    marge = joueur.potentiel - note_globale(joueur, cfg.attributs)

    facteur_age = facteur_par_age(age, cfg_prog.courbe_age)
    facteur_jeu = cfg_prog.facteur_jeu_min + (1 - cfg_prog.facteur_jeu_min) * min(
        minutes_mois / cfg_prog.minutes_reference_par_mois, 1.0
    )
    delta = facteur_age * facteur_jeu * (marge / 100) * cfg_prog.amplitude + rng.gauss(0, cfg_prog.bruit_ecart_type)

    _appliquer_delta(joueur, delta, marge, cfg)


def _appliquer_delta(joueur: Joueur, delta: float, marge: float, cfg: Config) -> None:
    bornes = cfg.attributs.bornes
    cfg_prog = cfg.demographie.progression

    if delta >= 0:
        delta_effectif = min(delta, max(marge, 0.0)) if cfg_prog.plafonne_par_potentiel else delta
        for nom in NOMS_ATTRIBUTS:
            valeur = joueur.attributs.valeur(nom) + delta_effectif
            setattr(joueur.attributs, nom, round(min(valeur, bornes.max)))
    else:
        poids = cfg_prog.poids_declin_par_attribut
        for nom in NOMS_ATTRIBUTS:
            valeur = joueur.attributs.valeur(nom) + delta * poids.get(nom, 1.0)
            setattr(joueur.attributs, nom, round(max(valeur, bornes.min)))
