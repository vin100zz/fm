"""Entry point: data/clubs.csv + data/players.csv -> a validated Monde.

See docs/modele-donnees.md ("Données fournies par l'utilisateur" and
"Validation au chargement") and docs/architecture.md ("Chargement des
données") for the pipeline this module orchestrates.
"""

from pathlib import Path
from random import Random

from core.ai.budgets import effectifs_par_club, masse_salariale_max_reelle
from core.config.modeles.racine import Config
from core.domain.date import Date
from core.domain.historique import Historique
from core.domain.monde import Monde
from core.world.importation import construction, limitation, validation
from core.world.importation.lecteurs import lire_clubs, lire_joueurs

__all__ = ["importer_monde"]


def importer_monde(
    dossier_donnees: Path, cfg: Config, date_debut: Date, graine: int, rng: Random
) -> tuple[Monde, list[str]]:
    """Read, synthesize, assemble and validate. Raises ImportInvalide on
    any blocking problem; otherwise returns the Monde plus every
    non-fatal warning collected along the way (`rng` drives the v0
    synthesis, `graine` is only stored on Monde for save reproducibility
    — the caller must keep them consistent, i.e. `rng = Random(graine)`).
    """
    lignes_clubs = lire_clubs(dossier_donnees / "clubs.csv")
    lignes_joueurs = lire_joueurs(dossier_donnees / "players.csv")

    avertissements: list[str] = []

    clubs = {}
    for ligne in lignes_clubs:
        club = construction.construire_club(ligne, cfg, rng)
        clubs[club.id] = club

    joueurs = {}
    for ligne in lignes_joueurs:
        club_id_brut = int(ligne["Club ID"])
        if club_id_brut != -1 and club_id_brut not in clubs:
            avertissements.append(
                f"joueur {ligne['Unique ID']}: club_id {club_id_brut} introuvable dans clubs.csv, joueur ignore"
            )
            continue
        joueur = construction.construire_joueur(ligne, cfg, date_debut, rng, avertissements)
        joueurs[joueur.id] = joueur

    competitions = construction.construire_competitions(clubs, cfg.monde)

    avertissements += limitation.limiter_effectifs_actifs(
        joueurs, clubs, cfg.attributs, cfg.ia.garde_fous.effectif_max
    )

    # Le plafond salarial calcule dans construction.construire_club (a
    # partir de la seule reputation, avant que le moindre joueur existe)
    # sert desormais de plancher : on le remplace par la masse salariale
    # reellement importee (+ marge) des lors qu'elle est plus genereuse
    # — voir core.ai.budgets.masse_salariale_max_reelle.
    _, masses_salariales = effectifs_par_club(joueurs.values())
    for club in clubs.values():
        club.masse_salariale_max = masse_salariale_max_reelle(
            masses_salariales.get(club.id, 0), club.masse_salariale_max, cfg
        )

    prochain_id = 1 + max(
        max(joueurs, default=0), max(clubs, default=0), max(competitions, default=0)
    )

    monde = Monde(
        date=date_debut,
        saison=1,
        graine=graine,
        joueurs=joueurs,
        clubs=clubs,
        competitions=competitions,
        historique=Historique(),
        prochain_id=prochain_id,
    )

    avertissements += validation.valider(
        monde, cfg.monde.competitions_simulees, cfg.ia.garde_fous.effectif_max
    )
    return monde, avertissements
