"""A team's playing strength for one match.

Deliberately minimal for step 3: only what the analytical engine needs
(docs/moteur-match.md — "calcule une force d'attaque et de défense par
équipe"). The possession engine (step 5) needs far more — a starting XI,
a formation, hauteur de bloc — and will extend this dataclass rather
than replace it, the same way Monde grew a `matches` field once the
engine existed to fill it.
"""

from dataclasses import dataclass

from core.config.modeles.racine import Config
from core.domain.joueur import Joueur
from core.world.note_globale import note_globale


@dataclass(frozen=True, slots=True)
class Equipe:
    club_id: int
    force_attaque: float
    force_defense: float


def equipe_depuis_effectif(club_id: int, joueurs: dict[int, Joueur], cfg: Config) -> Equipe:
    """Force = a note_globale average over the club's best players (as
    many as would start a match, config/monde.json ->
    regles_match.joueurs_sur_terrain), weighted per poste by its
    involvement in attack/defense (config/implications.json — reused
    rather than inventing a separate attack/defense poste classification).
    """
    effectif = [joueur for joueur in joueurs.values() if joueur.club_id == club_id]
    effectif.sort(key=lambda joueur: note_globale(joueur, cfg.attributs), reverse=True)
    meilleurs = effectif[: cfg.monde.regles_match.joueurs_sur_terrain]

    if not meilleurs:
        plancher = cfg.attributs.bornes.min
        return Equipe(club_id=club_id, force_attaque=plancher, force_defense=plancher)

    return Equipe(
        club_id=club_id,
        force_attaque=_force_ponderee(meilleurs, cfg.implications.vertical_attaque, cfg),
        force_defense=_force_ponderee(meilleurs, cfg.implications.vertical_defense, cfg),
    )


def _force_ponderee(meilleurs: list[Joueur], poids_par_poste: dict[str, list[float]], cfg: Config) -> float:
    poids_total = 0.0
    somme_ponderee = 0.0
    for joueur in meilleurs:
        poids = sum(poids_par_poste[joueur.poste.value])
        poids_total += poids
        somme_ponderee += poids * note_globale(joueur, cfg.attributs)

    if poids_total == 0:
        return cfg.attributs.bornes.min
    return somme_ponderee / poids_total
