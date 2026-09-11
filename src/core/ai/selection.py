"""Match-day squad selection and mid-match substitutions — "Sélection
de la composition" in docs/ia-gestion.md §8 and "Décision de
remplacement (IA)" in docs/etats-joueur.md. The real AI logic
core/engine/equipe.py::composition_depuis_effectif explicitly deferred
until an AIController existed.
"""

from core.config.modeles.racine import Config
from core.config.modeles.ia_gestion import SelectionConfig
from core.domain.club import Club
from core.domain.etat_match import EtatMatch
from core.domain.joueur import Joueur
from core.domain.poste import Poste
from core.domain.remplacement import Remplacement
from core.engine.composites import malus_hors_poste
from core.engine.equipe import Equipe, PositionOnze, force_ponderee
from core.world.note_globale import note_globale

POSTES_OFFENSIFS = frozenset({Poste.BU, Poste.AILG, Poste.AILD, Poste.MOC})
POSTES_DEFENSIFS = frozenset({Poste.GB, Poste.DC, Poste.DL, Poste.DR, Poste.MDC})


def choisir_composition(club: Club, effectif: list[Joueur], adversaire: Club, domicile: bool, cfg: Config) -> Equipe:
    disponibles = [joueur for joueur in effectif if joueur.blessure is None and joueur.suspension is None]

    formation = club.formation_preferee
    if len(disponibles) < cfg.monde.regles_match.joueurs_sur_terrain:
        formation = _meilleure_formation_disponible(disponibles, cfg)

    onze = _selectionner_onze(disponibles, formation, cfg.ia.selection, cfg)
    joueurs_onze = [position.joueur for position in onze]

    return Equipe(
        club_id=club.id,
        force_attaque=force_ponderee(joueurs_onze, cfg.implications.vertical_attaque, cfg),
        force_defense=force_ponderee(joueurs_onze, cfg.implications.vertical_defense, cfg),
        onze=tuple(onze),
        formation=formation,
        hauteur_bloc=_hauteur_bloc(club, adversaire, domicile, cfg),
    )


def _score_selection(joueur: Joueur, poste_slot: Poste, cfg_sel: SelectionConfig, cfg: Config) -> float:
    composite = max(note_globale(joueur, cfg.attributs), 1e-6)
    return (
        composite**cfg_sel.poids_composite
        * max(joueur.forme, 1e-6) ** cfg_sel.poids_forme
        * max(joueur.fatigue, 1e-6) ** cfg_sel.poids_fatigue
        * malus_hors_poste(joueur, poste_slot, cfg.attributs)
    )


def _selectionner_onze(
    disponibles: list[Joueur], formation: str, cfg_sel: SelectionConfig, cfg: Config
) -> list[PositionOnze]:
    slots = [Poste(code) for code in cfg.formations.formations[formation]]
    onze: list[PositionOnze] = []
    deja_choisis: set[int] = set()

    for poste_slot in slots:
        candidats = sorted(
            (joueur for joueur in disponibles if joueur.id not in deja_choisis),
            key=lambda joueur: _score_selection(joueur, poste_slot, cfg_sel, cfg),
            reverse=True,
        )
        choisi = candidats[0]
        # Rotation (docs/ia-gestion.md §8.4): a tired starter with a
        # near-equal backup rests, rather than always fielding the
        # nominal best XI regardless of fitness.
        if len(candidats) > 1 and choisi.fatigue < cfg_sel.seuil_rotation_fatigue:
            doublure = candidats[1]
            ecart = note_globale(choisi, cfg.attributs) - note_globale(doublure, cfg.attributs)
            if ecart <= cfg_sel.ecart_niveau_acceptable_rotation:
                choisi = doublure

        onze.append(PositionOnze(poste=poste_slot, joueur=choisi))
        deja_choisis.add(choisi.id)
    return onze


def _meilleure_formation_disponible(disponibles: list[Joueur], cfg: Config) -> str:
    meilleur_score, meilleure_formation = -1.0, next(iter(cfg.formations.formations))
    for nom_formation in cfg.formations.formations:
        onze = _selectionner_onze(disponibles, nom_formation, cfg.ia.selection, cfg)
        score = sum(note_globale(position.joueur, cfg.attributs) for position in onze)
        if score > meilleur_score:
            meilleur_score, meilleure_formation = score, nom_formation
    return meilleure_formation


def _hauteur_bloc(club: Club, adversaire: Club, domicile: bool, cfg: Config) -> float:
    cfg_sel = cfg.ia.selection
    hauteur = cfg_sel.poids_ecart_reputation_bloc * (club.reputation - adversaire.reputation)
    if domicile:
        hauteur += cfg_sel.bonus_bloc_domicile
    cfg_hb = cfg.formations.hauteur_bloc
    return min(max(hauteur, cfg_hb.min), cfg_hb.max)


def decider_remplacement(
    etat: EtatMatch, joueurs_avertis: frozenset[int], remplacements_max: int, cfg: Config
) -> Remplacement | None:
    """Priority order from docs/etats-joueur.md: injury first, then low
    fatigue, then a booked defender at risk of a second yellow, then two
    scoreline-driven tactical tweaks. Evaluated every
    `intervalle_evaluation_minutes` from `premiere_minute_evaluation` —
    the caller (core/engine/match.py) decides when to call this, not this
    function.
    """
    cfg_r = cfg.etats.remplacements
    if etat.remplacements_effectues >= remplacements_max or not etat.banc:
        return None

    blesse = next((joueur for joueur in etat.onze_actuel if joueur.blessure is not None), None)
    if blesse is not None:
        remplacant = _meilleur_remplacant(blesse, etat.banc, cfg)
        if remplacant is not None:
            return Remplacement(blesse.id, remplacant.id, etat.minute, "blessure")

    for joueur in sorted(etat.onze_actuel, key=lambda joueur: joueur.fatigue):
        if joueur.fatigue >= cfg_r.seuil_fatigue_declenchement:
            break
        remplacant = _meilleur_remplacant(joueur, etat.banc, cfg, cfg_r.ecart_niveau_acceptable_remplacant)
        if remplacant is not None:
            return Remplacement(joueur.id, remplacant.id, etat.minute, "fatigue")

    for joueur in etat.onze_actuel:
        if (
            joueur.id in joueurs_avertis
            and joueur.fatigue < cfg_r.seuil_fatigue_joueur_averti
            and joueur.poste in POSTES_DEFENSIFS
        ):
            remplacant = _meilleur_remplacant(joueur, etat.banc, cfg, cfg_r.ecart_niveau_acceptable_remplacant)
            if remplacant is not None:
                return Remplacement(joueur.id, remplacant.id, etat.minute, "risque de second jaune")

    minutes_restantes = 90 - etat.minute
    if etat.buts_pour < etat.buts_contre and minutes_restantes <= cfg_r.minutes_restantes_ajustement_tactique:
        remplacement = _ajustement_par_profil(etat, POSTES_OFFENSIFS, "ajustement tactique", cfg)
        if remplacement is not None:
            return remplacement

    if etat.buts_pour - etat.buts_contre >= cfg_r.ecart_buts_ajustement_defensif:
        remplacement = _ajustement_par_profil(etat, POSTES_DEFENSIFS, "gestion du score", cfg)
        if remplacement is not None:
            return remplacement

    return None


def _meilleur_remplacant(
    sortant: Joueur, banc: tuple[Joueur, ...], cfg: Config, ecart_max: float | None = None
) -> Joueur | None:
    if not banc:
        return None
    candidats = sorted(
        banc,
        key=lambda joueur: note_globale(joueur, cfg.attributs) * malus_hors_poste(joueur, sortant.poste, cfg.attributs),
        reverse=True,
    )
    meilleur = candidats[0]
    if ecart_max is not None:
        ecart = note_globale(sortant, cfg.attributs) - note_globale(meilleur, cfg.attributs)
        if ecart > ecart_max:
            return None
    return meilleur


def _ajustement_par_profil(
    etat: EtatMatch, postes_cibles: frozenset[Poste], motif: str, cfg: Config
) -> Remplacement | None:
    entrant = max(
        (joueur for joueur in etat.banc if joueur.poste in postes_cibles),
        key=lambda joueur: note_globale(joueur, cfg.attributs),
        default=None,
    )
    sortant = min(
        (joueur for joueur in etat.onze_actuel if joueur.poste not in postes_cibles),
        key=lambda joueur: joueur.fatigue,
        default=None,
    )
    if entrant is None or sortant is None:
        return None
    return Remplacement(sortant.id, entrant.id, etat.minute, motif)
