"""Zone/couloir aggregate notes for one Equipe. See "Agrégats de zone"
in docs/moteur-match.md — separating quality from density is the part
that makes formations matter (a 5-4-1 must not simply out-number a
4-3-3 in defence). Recomputed once per team at kickoff; the engine
recomputes it again only on a substitution or a red card (docs) — not
on every possession.
"""

from dataclasses import dataclass

from core.config.modeles.moteur_match import DensiteConfig
from core.config.modeles.racine import Config
from core.domain.geometrie import COULOIRS_ORDONNES, ZONES_ORDONNEES, Couloir, Zone
from core.engine.composites import composite, malus_hors_poste
from core.engine.equipe import Equipe, PositionOnze
from core.engine.implication import TablesImplication


@dataclass(frozen=True, slots=True)
class NotesEquipe:
    progression_attaque: dict[Zone, dict[Couloir, float]]
    progression_defense: dict[Zone, dict[Couloir, float]]
    occasion_attaque: dict[Zone, dict[Couloir, float]]
    occasion_defense: dict[Zone, dict[Couloir, float]]


def facteur_densite(densite: float, cfg: DensiteConfig) -> float:
    return (densite / cfg.reference) ** cfg.exposant


def multiplicateur_moral(moral: float, cfg_moral) -> float:
    """No formula is given in docs/etats-joueur.md beyond "amplitude
    effet match limitée à ±5%" — this linearly maps the configured moral
    range onto [1-amplitude, 1+amplitude], symmetric around its midpoint.
    """
    centre = (cfg_moral.min + cfg_moral.max) / 2
    demi_etendue = (cfg_moral.max - cfg_moral.min) / 2
    ecart_normalise = (moral - centre) / demi_etendue if demi_etendue else 0.0
    return 1.0 + cfg_moral.amplitude_effet_match * ecart_normalise


def multiplicateurs_joueurs(onze: tuple[PositionOnze, ...], cfg: Config) -> dict[int, float]:
    """forme * fatigue * moral * malus_hors_poste, once per player — these
    don't vary by zone/couloir, only composite() and implication() do.
    """
    return {
        position.joueur.id: (
            position.joueur.forme
            * position.joueur.fatigue
            * multiplicateur_moral(position.joueur.moral, cfg.etats.moral)
            * malus_hors_poste(position.joueur, position.poste, cfg.attributs)
        )
        for position in onze
    }


def note_zone(
    onze: tuple[PositionOnze, ...],
    zone: Zone,
    couloir: Couloir,
    phase_attaque: bool,
    nom_composite: str,
    tables: TablesImplication,
    multiplicateurs: dict[int, float],
    cfg: Config,
) -> float:
    poids = [tables.implication(position.poste, zone, couloir, phase_attaque) for position in onze]
    densite = sum(poids)
    if densite == 0:
        return cfg.moteur.densite.note_plancher

    qualite = sum(
        p * composite(position.joueur, nom_composite, cfg.attributs) * multiplicateurs[position.joueur.id]
        for p, position in zip(poids, onze, strict=True)
    ) / densite

    return qualite * facteur_densite(densite, cfg.moteur.densite)


def calculer_notes_equipe(equipe: Equipe, tables: TablesImplication, cfg: Config) -> NotesEquipe:
    multiplicateurs = multiplicateurs_joueurs(equipe.onze, cfg)

    def grille(phase_attaque: bool, nom_composite: str) -> dict[Zone, dict[Couloir, float]]:
        return {
            zone: {
                couloir: note_zone(
                    equipe.onze, zone, couloir, phase_attaque, nom_composite, tables, multiplicateurs, cfg
                )
                for couloir in COULOIRS_ORDONNES
            }
            for zone in ZONES_ORDONNEES
        }

    return NotesEquipe(
        progression_attaque=grille(True, "progression_attaque"),
        progression_defense=grille(False, "progression_defense"),
        occasion_attaque=grille(True, "occasion_attaque"),
        occasion_defense=grille(False, "occasion_defense"),
    )
