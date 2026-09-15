"""Contract satisfaction and renewal — same engine as mercato but
without a buying club, evaluated weekly. See "Contrats et
renouvellements" in docs/ia-gestion.md.
"""

from dataclasses import dataclass

from core.ai.besoins import niveau_cible
from core.ai.utilite import utilite
from core.ai.valorisation import valeur
from core.config.modeles.ia_gestion import ContratsConfig
from core.config.modeles.racine import Config
from core.domain.club import Club
from core.domain.date import Date
from core.domain.joueur import Joueur
from core.world.note_globale import note_globale


@dataclass(frozen=True, slots=True)
class DecisionRenouvellement:
    ouvre_negociation: bool
    renouvelle: bool
    salaire_demande: int
    duree_annees: int


def salaire_attendu(joueur: Joueur, date_actuelle: Date, cfg: Config) -> int:
    return round(valeur(joueur, date_actuelle, cfg) * cfg.ia.contrats.ratio_salaire_hebdo_sur_valeur)


def satisfaction(
    joueur: Joueur, club: Club, minutes_saison: float, minutes_attendues: float, date_actuelle: Date, cfg: Config
) -> float:
    """docs/ia-gestion.md's `reputation_attendue(joueur)` has no formula —
    reuses note_globale directly (both are on the same 1-100 scale, and
    a player's expected club prestige naturally tracks their own level).
    """
    cfg_c = cfg.ia.contrats
    assert joueur.contrat is not None

    s_salaire = joueur.contrat.salaire_hebdo / salaire_attendu(joueur, date_actuelle, cfg)
    s_jeu = minutes_saison / minutes_attendues if minutes_attendues else 1.0
    reputation_attendue = note_globale(joueur, cfg.attributs)
    s_club = club.reputation / reputation_attendue if reputation_attendue else 1.0

    return (
        cfg_c.poids_salaire * _clamp(s_salaire, 0.0, 1.5)
        + cfg_c.poids_temps_de_jeu * _clamp(s_jeu, 0.0, 1.5)
        + cfg_c.poids_club * _clamp(s_club, 0.0, 1.5)
    )


def decision_renouvellement(
    joueur: Joueur,
    club: Club,
    effectif: list[Joueur],
    minutes_saison: float,
    minutes_attendues: float,
    date_actuelle: Date,
    cfg: Config,
) -> DecisionRenouvellement:
    """docs: "Satisfaction < 0.65 ou contrat à moins de 12 mois → ouverture
    d'une négociation" ; "le club renouvelle si utilite(joueur, club)
    justifie le coût sur la durée" — the cost check is undefined, so we
    treat it as "positive marginal utility AND the demanded wage keeps
    the club under its (strict, per garde_fous) wage cap", reusing the
    club's actual wage bill from `effectif` rather than inventing a
    separate cost/duration amortisation model.

    **Renews if the player still clears the club's general level bar,
    not just if `utilite() > 0` (2026-09-11, revised)**: same root cause
    as `core/world/mercato.py::_meilleur_candidat`'s acceptance
    criterion — `utilite()` routes through `meilleure_affectation`, a
    *greedy* per-slot assignment, so a squad already saturated with
    excellent players (Real Madrid, Barcelona, Man City-caliber
    depth) can show ~0 or negative marginal gain from keeping ONE more
    great player, even though they plainly deserve their spot. Measured
    on the real dataset: elite clubs collapsed to single-digit squads
    over 4 simulated seasons specifically because their own best
    players kept failing this check and expired into free agency for
    nothing. Kept as an OR, not a replacement, so a squad-depth player
    who doesn't clear the bar can still be renewed on genuine marginal
    value.
    """
    cfg_c = cfg.ia.contrats
    assert joueur.contrat is not None

    mois_restants = date_actuelle.jours_jusqua(joueur.contrat.date_fin) / 30.44
    ouvre = (
        satisfaction(joueur, club, minutes_saison, minutes_attendues, date_actuelle, cfg)
        < cfg_c.seuil_satisfaction_negociation
        or mois_restants <= cfg_c.mois_avant_fin_declenchant
    )
    if not ouvre:
        return DecisionRenouvellement(
            ouvre_negociation=False, renouvelle=False, salaire_demande=joueur.contrat.salaire_hebdo, duree_annees=0
        )

    salaire_demande = round(salaire_attendu(joueur, date_actuelle, cfg) * (1 + cfg_c.facteur_ego * _ego(joueur, cfg)))
    duree_annees = duree_par_age(joueur.date_naissance.age_a(date_actuelle), cfg_c)

    masse_salariale_sans = sum(
        autre.contrat.salaire_hebdo for autre in effectif if autre.contrat is not None and autre.id != joueur.id
    )
    sous_plafond = (
        not cfg.ia.garde_fous.plafond_salarial_strict
        or masse_salariale_sans + salaire_demande <= club.masse_salariale_max
    )
    comble_le_niveau = note_globale(joueur, cfg.attributs) >= niveau_cible(club, cfg)
    renouvelle = sous_plafond and (comble_le_niveau or utilite(joueur, club, effectif, date_actuelle, cfg) > 0)

    return DecisionRenouvellement(
        ouvre_negociation=True, renouvelle=renouvelle, salaire_demande=salaire_demande, duree_annees=duree_annees
    )


def _ego(joueur: Joueur, cfg: Config) -> float:
    """No `ego` attribute exists on Joueur (docs never defines one) —
    approximated from how far above-average the player's own level is,
    on the same idea as valorisation's talent convexity: better players
    demand more.
    """
    return min(max((note_globale(joueur, cfg.attributs) - 50) / 50, 0.0), 1.0)


def duree_par_age(age: int, cfg_c: ContratsConfig) -> int:
    """Public: also used by core/ai/mercato.py for a freshly-signed
    transfer contract, not just a renewal.
    """
    for palier in sorted(cfg_c.duree_proposee_par_age, key=lambda p: p.age_max):
        if age <= palier.age_max:
            return palier.annees
    return cfg_c.duree_proposee_par_age[-1].annees


def _clamp(valeur: float, minimum: float, maximum: float) -> float:
    return min(max(valeur, minimum), maximum)
