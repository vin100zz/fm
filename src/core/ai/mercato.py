"""Transfer-window decision primitives — "Réponse du vendeur" and
"Choix du joueur" in docs/ia-gestion.md. Deliberately stops at pure,
testable functions: the multi-club negotiation loop ("tour_mercato")
needs a season/calendar orchestrator that doesn't exist yet (see
docs/ia-gestion.md §5), so it is not built here.

`repondre_offre_dormant` (docs/progression-demographie.md's "Marché
extérieur") is the equivalent for the ~25 900 dormant clubs: they skip
the full patience/surplus negotiation a real `Club` stance drives,
using a flat probabilistic heuristic instead
(`ia_gestion.mercato.clubs_dormants`).
"""

from random import Random

from core.ai.besoins import profondeur_utile, projeter_temps_jeu, rang_au_poste
from core.ai.contrats import salaire_attendu
from core.ai.valorisation import valeur
from core.config.modeles.racine import Config
from core.domain.club import Club
from core.domain.date import Date
from core.domain.joueur import Joueur
from core.domain.offre import Offre, Reponse, TypeReponse


def surplus(joueur: Joueur, effectif: list[Joueur], cfg: Config) -> float:
    """0 = indispensable starter, 1 = at or beyond the poste's useful
    depth. docs/ia-gestion.md's `surplus(club, joueur)` has no formula —
    reuses the depth-chart rank besoins.py already computes for
    `projeter_temps_jeu`, on the same "useful depth" notion.
    """
    profondeur = profondeur_utile(joueur.poste, cfg)
    rang = rang_au_poste(joueur, effectif, cfg)
    return min(rang / max(profondeur - 1, 1), 1.0)


def repondre_offre(
    offre: Offre, club: Club, joueur: Joueur, effectif: list[Joueur], date_actuelle: Date, cfg: Config
) -> Reponse:
    cfg_m = cfg.ia.mercato
    seuil = valeur(joueur, date_actuelle, cfg) * (
        cfg_m.seuil_vendeur_multiplicateur - cfg_m.seuil_vendeur_reduction_surplus * surplus(joueur, effectif, cfg)
    )
    seuil *= 1 + cfg_m.poids_patience_negociation * club.personnalite.patience_negociation

    if offre.montant >= seuil:
        return Reponse(TypeReponse.ACCEPTE)
    if offre.montant >= seuil * cfg_m.ratio_contre_offre:
        return Reponse(TypeReponse.CONTRE_OFFRE, contre_montant=round(seuil))
    return Reponse(TypeReponse.REFUSE)


def repondre_offre_dormant(offre: Offre, joueur: Joueur, date_actuelle: Date, cfg: Config, rng: Random) -> Reponse:
    cfg_d = cfg.ia.mercato.clubs_dormants
    prix_demande = valeur(joueur, date_actuelle, cfg) * cfg_d.multiplicateur_prix_demande
    if offre.montant >= prix_demande and rng.random() < cfg_d.probabilite_acceptation_offre_au_prix:
        return Reponse(TypeReponse.ACCEPTE)
    return Reponse(TypeReponse.REFUSE)


def score_offre(
    joueur: Joueur,
    club: Club,
    salaire_propose: int,
    effectif_cible: list[Joueur],
    date_actuelle: Date,
    cfg: Config,
    rng: Random,
) -> float:
    """docs: "temps_jeu_projete compare le niveau du joueur à l'effectif
    d'accueil à son poste" — evaluated with the player hypothetically
    already in `effectif_cible`, same as besoins.projeter_temps_jeu is
    used elsewhere for "would this player start here".
    `ambition_sportive(club)` has no formula either — reused from
    `club.personnalite.agressivite_salariale`, already a 0-1-ish trait
    reflecting how aggressively a club competes for players.
    """
    cfg_sj = cfg.ia.mercato.score_joueur

    ratio_salaire = min(salaire_propose / salaire_attendu(joueur, date_actuelle, cfg), 1.0)
    temps_jeu = projeter_temps_jeu(joueur, [*effectif_cible, joueur], cfg)
    ambition_sportive = club.personnalite.agressivite_salariale

    score = (
        cfg_sj.poids_salaire * ratio_salaire
        + cfg_sj.poids_temps_de_jeu * temps_jeu
        + cfg_sj.poids_reputation_club * (club.reputation / 100)
        + cfg_sj.poids_ambition * ambition_sportive
    )
    return score + rng.gauss(0.0, cfg_sj.bruit_ecart_type)
