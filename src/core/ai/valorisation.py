"""Player valorisation — the price reference everything else (utility,
mercato offers, contract negotiation) is built on. See "Valeur
intrinsèque" in docs/ia-gestion.md.
"""

import math

from core.config.modeles.racine import Config
from core.domain.club import Club
from core.domain.date import Date
from core.domain.fourchette import Fourchette
from core.domain.joueur import Joueur
from core.world.note_globale import note_globale
from core.world.progression import facteur_par_age


def estimation_potentiel(
    joueur: Joueur, date_actuelle: Date, cfg: Config, club_observateur: Club | None = None
) -> Fourchette:
    """The stored `potentiel` is the true value — neither the AI nor the
    UI ever reads it directly (docs/progression-demographie.md). Noise
    shrinks linearly from `bruit_max` (at age_debut_convergence) to 0
    (at age_convergence), and widens again for a lower-reputation
    observer club.
    """
    cfg_est = cfg.demographie.estimation_potentiel
    age = joueur.date_naissance.age_a(date_actuelle)
    largeur = max(cfg_est.age_convergence - cfg_est.age_debut_convergence, 1)
    ratio_convergence = min(max(age - cfg_est.age_debut_convergence, 0), largeur) / largeur
    bruit = cfg_est.bruit_max * (1 - ratio_convergence)

    if club_observateur is not None:
        bruit *= cfg_est.base_facteur_observateur - cfg_est.facteur_reputation_observateur * (
            club_observateur.reputation / 100
        )

    return Fourchette(joueur.potentiel - bruit, joueur.potentiel + bruit)


def valeur(joueur: Joueur, date_actuelle: Date, cfg: Config) -> int:
    """Deliberately convex in talent (docs: "un joueur à 90 ne vaut pas
    1.2 fois un joueur à 75, il vaut environ 5 fois plus") — without
    that, big clubs would buy ten good players instead of one star.
    """
    cfg_valo = cfg.ia.valorisation
    niveau = note_globale(joueur, cfg.attributs)
    potentiel_estime = estimation_potentiel(joueur, date_actuelle, cfg).milieu

    base = cfg_valo.base_euros * math.exp(
        cfg_valo.exposant
        * (max(niveau, potentiel_estime * cfg_valo.poids_potentiel_sur_niveau) - cfg_valo.niveau_reference)
    )
    facteur_age = facteur_par_age(joueur.date_naissance.age_a(date_actuelle), cfg_valo.courbe_age)
    rarete = cfg_valo.rarete_poste.get(joueur.poste.value, 1.0)

    montant = base * facteur_age * rarete
    if joueur.contrat is not None:
        montant *= _decote_fin_contrat(joueur.contrat.date_fin, date_actuelle, cfg_valo)
    return round(montant)


def _decote_fin_contrat(date_fin: Date, date_actuelle: Date, cfg_valo) -> float:
    jours_restants = date_actuelle.jours_jusqua(date_fin)
    mois_restants = jours_restants / 30.44  # jours moyens par mois, constante calendaire

    for palier in sorted(cfg_valo.decote_fin_contrat, key=lambda p: p.mois_max):
        if mois_restants < palier.mois_max:
            return palier.facteur
    return 1.0
