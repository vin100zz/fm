"""One possession's state machine: progress zone by zone until a
chance is created and resolved, or the ball is lost. See "Machine à
états d'une possession" in docs/moteur-match.md.
"""

import math
from dataclasses import dataclass
from random import Random

from core.config.modeles.moteur_match import TurnoverConfig
from core.config.modeles.racine import Config
from core.domain.geometrie import Couloir, Zone, zone_suivante
from core.domain.match import Evenement
from core.engine.couloirs import peut_changer_aile
from core.engine.equipe import PositionOnze
from core.engine.implication import TablesImplication
from core.engine.notes_zones import NotesEquipe
from core.engine.occasion import resoudre_occasion


@dataclass(frozen=True, slots=True)
class ResultatPossession:
    evenements: tuple[Evenement, ...]
    but: bool
    zone_fin: Zone
    couloir_fin: Couloir
    xg: float = 0.0


def reussite(x: float, rng: Random, biais: float = 0.0) -> bool:
    return rng.random() < 1 / (1 + math.exp(-(x + biais)))


def _malus_contre(couloir_courant: Couloir, couloir_origine: Couloir, cfg: TurnoverConfig) -> float:
    malus = cfg.malus_defensif_contre
    if couloir_courant is couloir_origine:
        malus += cfg.malus_defensif_couloir_concerne
    return malus


def jouer_possession(
    zone: Zone,
    couloir: Couloir,
    est_contre: bool,
    couloir_origine_contre: Couloir | None,
    onze_attaquant: tuple[PositionOnze, ...],
    onze_defenseur: tuple[PositionOnze, ...],
    notes_attaquant: NotesEquipe,
    notes_defenseur: NotesEquipe,
    est_domicile_attaquant: bool,
    minute: int,
    tables: TablesImplication,
    cfg: Config,
    rng: Random,
) -> ResultatPossession:
    cfg_transitions = cfg.moteur.transitions

    while True:
        if zone is not Zone.VERITE:
            force_attaque = notes_attaquant.progression_attaque[zone][couloir]
            force_defense = notes_defenseur.progression_defense[zone][couloir]
            if est_contre and couloir_origine_contre is not None:
                force_defense -= _malus_contre(couloir, couloir_origine_contre, cfg.moteur.turnover)

            bonus = cfg_transitions.bonus_domicile if est_domicile_attaquant else 0.0
            if not reussite(cfg_transitions.k_prog * (force_attaque - force_defense) + bonus, rng):
                return ResultatPossession(evenements=(), but=False, zone_fin=zone, couloir_fin=couloir)

            zone = zone_suivante(zone)
            vision_moyenne = sum(position.joueur.attributs.vision for position in onze_attaquant) / len(
                onze_attaquant
            )
            couloir = peut_changer_aile(couloir, vision_moyenne, cfg.moteur.couloirs, rng)
        else:
            force_attaque = notes_attaquant.occasion_attaque[zone][couloir]
            force_defense = notes_defenseur.occasion_defense[zone][couloir]
            if est_contre and couloir_origine_contre is not None:
                force_defense -= _malus_contre(couloir, couloir_origine_contre, cfg.moteur.turnover)

            if not reussite(cfg_transitions.k_occ * (force_attaque - force_defense), rng):
                return ResultatPossession(evenements=(), but=False, zone_fin=zone, couloir_fin=couloir)

            resultat = resoudre_occasion(
                minute, couloir, est_contre, onze_attaquant, onze_defenseur, tables, cfg, rng
            )
            return ResultatPossession(
                evenements=resultat.evenements,
                but=resultat.but,
                zone_fin=zone,
                couloir_fin=couloir,
                xg=resultat.xg,
            )
