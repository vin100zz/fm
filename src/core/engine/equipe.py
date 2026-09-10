"""A team as the match engines see it.

`force_attaque`/`force_defense` are all the analytical engine (step 3)
needs. The possession engine (step 5) needs far more — a starting XI
assigned to formation slots, and a hauteur de bloc — added here as an
extension rather than a new type, per the plan noted back in step 3.
"""

from dataclasses import dataclass

from core.config.modeles.racine import Config
from core.domain.joueur import Joueur
from core.domain.poste import Poste
from core.engine.composites import malus_hors_poste
from core.world.note_globale import note_globale


@dataclass(frozen=True, slots=True)
class PositionOnze:
    poste: Poste  # the formation slot's poste — may differ from joueur.poste
    joueur: Joueur


@dataclass(frozen=True, slots=True)
class Equipe:
    club_id: int
    force_attaque: float
    force_defense: float
    onze: tuple[PositionOnze, ...] = ()
    formation: str = ""
    hauteur_bloc: float = 0.0


def equipe_depuis_effectif(club_id: int, joueurs: dict[int, Joueur], cfg: Config) -> Equipe:
    """Force = a note_globale average over the club's best players (as
    many as would start a match, config/monde.json ->
    regles_match.joueurs_sur_terrain), weighted per poste by its
    involvement in attack/defense (config/implications.json — reused
    rather than inventing a separate attack/defense poste classification).
    Used by the analytical engine only: no onze, no formation.
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


def composition_depuis_effectif(
    club_id: int, joueurs: dict[int, Joueur], formation: str, hauteur_bloc: float, cfg: Config
) -> Equipe:
    """Fill each formation slot with the best available player for it
    (note_globale, discounted by malus_hors_poste if out of position).
    This is deliberately not the real selection AI (docs/ia-gestion.md
    §8 — fatigue-aware rotation, tactical adjustment): there is no
    AIController yet (step 7). A club's actual `formation_preferee` is
    the caller's job to pass in, same for hauteur_bloc.
    """
    slots = [Poste(code) for code in cfg.formations.formations[formation]]
    effectif = [joueur for joueur in joueurs.values() if joueur.club_id == club_id]

    onze: list[PositionOnze] = []
    deja_choisis: set[int] = set()
    for poste_slot in slots:
        candidats = [joueur for joueur in effectif if joueur.id not in deja_choisis]
        meilleur = max(
            candidats,
            key=lambda joueur: note_globale(joueur, cfg.attributs) * malus_hors_poste(joueur, poste_slot, cfg.attributs),
        )
        onze.append(PositionOnze(poste=poste_slot, joueur=meilleur))
        deja_choisis.add(meilleur.id)

    return Equipe(
        club_id=club_id,
        force_attaque=_force_ponderee([p.joueur for p in onze], cfg.implications.vertical_attaque, cfg),
        force_defense=_force_ponderee([p.joueur for p in onze], cfg.implications.vertical_defense, cfg),
        onze=tuple(onze),
        formation=formation,
        hauteur_bloc=hauteur_bloc,
    )
