"""MoteurPossession: orchestrates a full match possession by possession.
See "Structure de la simulation" in docs/moteur-match.md.

`ResultatMatch.notes` is filled in (step 6) — see `_calculer_notes` for
the rating formula, invented since docs doesn't give one. forme/fatigue
updates from those notes, and card-driven suspensions, are applied
*after* the match by core/world/appliquer_match.py, not here: the
engine returns events, it never mutates a Joueur's persistent state
directly (see "Mutation du monde" in docs/architecture.md) — the one
exception is a red card's immediate effect on `onze` *within this one
match*, which isn't persistent state.

Substitutions (step 7) are wired through an optional `bancs`/
`controleurs` pair on `simuler` — omitted (as every existing
calibration/benchmark/test call omits them), the match behaves exactly
as before. When present, each side is evaluated for a substitution at
`cfg.etats.remplacements.intervalle_evaluation_minutes` intervals via
`ClubController.decider_remplacement`, the same decision function
`core/ai/selection.py` exposes.

Deliberately still out of scope (documented, not silently skipped):
mid-match forme/fatigue dynamics (read once at kickoff; recalculating
notes_zones at fatigue paliers, per docs, needs that first),
in-match injuries (core/world/etats/blessures.py explains why, and
means `decider_remplacement`'s injury branch never fires from live
engine data yet), and hauteur de bloc's effect on recovery zone /
vulnerability to the counter (accepted on Equipe, not yet consumed).
A red card still
weakens a side for real: removing a player from onze and recomputing
notes_zones lets facteur_densite do the work, exactly as docs
prescribes — "aucun malus artificiel à ajouter" (the goalkeeper is
excluded from ever being sent off, see cartons.py — this model has no
way to put an outfield player in goal instead).
"""

from random import Random

from core.ai.controller import ClubController
from core.config.modeles.racine import Config
from core.domain.etat_match import EtatMatch
from core.domain.geometrie import Couloir, Zone
from core.domain.joueur import Joueur
from core.domain.match import Evenement, ResultatMatch, StatsEquipe, TypeEvenement
from core.engine.cartons import determiner_carton
from core.engine.chronologie import duree_possession, temps_additionnel
from core.engine.couloirs import choisir_couloir
from core.engine.coups_arretes import evaluer_coup_arrete
from core.engine.equipe import Equipe, PositionOnze
from core.engine.implication import construire_tables_implication
from core.engine.notes_zones import NotesEquipe, calculer_notes_equipe
from core.engine.possession import jouer_possession


class _EtatCote:
    """Per-side running state during one match — mutable on purpose
    (a red card replaces `equipe`/`notes`), unlike the frozen engine types.
    """

    def __init__(self, equipe: Equipe, notes: NotesEquipe, banc: tuple[Joueur, ...] = ()) -> None:
        self.onze_initial = equipe.onze
        self.equipe = equipe
        self.notes = notes
        self.banc: list[Joueur] = list(banc)
        self.remplacements_effectues = 0
        self.derniere_minute_evaluee = -1
        self.tirs = 0
        self.xg = 0.0
        self.corners = 0
        self.cartons_jaunes = 0
        self.cartons_rouges = 0
        self.possessions = 0
        self.jaunes_en_match: dict[int, int] = {}


class MoteurPossession:
    def simuler(
        self,
        dom: Equipe,
        ext: Equipe,
        cfg: Config,
        rng: Random,
        bancs: dict[bool, tuple[Joueur, ...]] | None = None,
        controleurs: dict[bool, ClubController] | None = None,
    ) -> ResultatMatch:
        tables = construire_tables_implication(cfg.implications)
        bancs = bancs or {}
        etats = {
            True: _EtatCote(dom, calculer_notes_equipe(dom, tables, cfg), bancs.get(True, ())),
            False: _EtatCote(ext, calculer_notes_equipe(ext, tables, cfg), bancs.get(False, ())),
        }

        evenements: list[Evenement] = []
        buts = {True: 0, False: 0}
        nb_arrets_de_jeu = 0

        cote_attaquant = rng.random() < 0.5
        zone, couloir, est_contre, couloir_origine_contre = self._engager(etats, cote_attaquant, cfg, rng)

        t = 0.0
        duree_reguliere = cfg.moteur.chronologie.duree_match_secondes
        duree_totale: float | None = None

        while True:
            t += duree_possession(cfg.moteur.chronologie, rng)
            if duree_totale is None and t >= duree_reguliere:
                duree_totale = duree_reguliere + temps_additionnel(nb_arrets_de_jeu, cfg.moteur.chronologie, rng)
            if t >= (duree_totale if duree_totale is not None else duree_reguliere):
                break
            minute = min(int(t // 60), 90)

            if controleurs is not None:
                for cote in (True, False):
                    if cote in controleurs:
                        self._evaluer_remplacement(
                            etats[cote], cote, minute, buts, controleurs[cote], tables, cfg, evenements
                        )

            attaquant, defenseur = etats[cote_attaquant], etats[not cote_attaquant]
            attaquant.possessions += 1

            resultat = jouer_possession(
                zone, couloir, est_contre, couloir_origine_contre,
                attaquant.equipe.onze, defenseur.equipe.onze,
                attaquant.notes, defenseur.notes,
                cote_attaquant, minute, tables, cfg, rng,
            )
            evenements.extend(resultat.evenements)
            self._compter_tirs(attaquant, resultat.evenements, resultat.xg)

            if resultat.but:
                buts[cote_attaquant] += 1
                nb_arrets_de_jeu += 1
                cote_attaquant = not cote_attaquant
                zone, couloir, est_contre, couloir_origine_contre = self._engager(etats, cote_attaquant, cfg, rng)
                continue

            if resultat.zone_fin is Zone.VERITE:
                resultat_cpa = evaluer_coup_arrete(
                    resultat.zone_fin, resultat.couloir_fin, minute,
                    attaquant.equipe.onze, defenseur.equipe.onze, tables, cfg, rng,
                )
                if resultat_cpa is not None:
                    evenements.extend(resultat_cpa.evenements)
                    self._compter_tirs(attaquant, resultat_cpa.evenements, resultat_cpa.xg)
                    if resultat_cpa.but:
                        buts[cote_attaquant] += 1
                        nb_arrets_de_jeu += 1
                        cote_attaquant = not cote_attaquant
                        zone, couloir, est_contre, couloir_origine_contre = self._engager(
                            etats, cote_attaquant, cfg, rng
                        )
                        continue

            carton = determiner_carton(
                resultat.zone_fin, resultat.couloir_fin, defenseur.equipe.onze, tables, cfg.moteur.cartons, rng,
                deja_avertis=frozenset(defenseur.jaunes_en_match),
            )
            if carton is not None:
                fauteur, couleur = carton
                detail = self._enregistrer_carton(defenseur, fauteur, couleur)
                evenements.append(
                    Evenement(minute, TypeEvenement.CARTON, fauteur.joueur.id, None, resultat.zone_fin, resultat.couloir_fin, detail=detail)
                )
                if detail != "jaune":
                    defenseur.cartons_rouges += 1
                    self._expulser(defenseur, fauteur, tables, cfg)
                else:
                    defenseur.cartons_jaunes += 1

            zone, couloir, est_contre, couloir_origine_contre = self._possession_suivante(resultat, est_contre, cfg)
            cote_attaquant = not cote_attaquant

        return ResultatMatch(
            buts_dom=buts[True],
            buts_ext=buts[False],
            evenements=evenements,
            stats_dom=self._stats(etats[True], etats[False]),
            stats_ext=self._stats(etats[False], etats[True]),
            notes=self._calculer_notes(evenements, etats[True].onze_initial, etats[False].onze_initial, cfg),
        )

    @staticmethod
    def _engager(
        etats: dict[bool, "_EtatCote"], cote_attaquant: bool, cfg: Config, rng: Random
    ) -> tuple[Zone, Couloir, bool, Couloir | None]:
        zone = Zone.DEFENSE
        attaquant, defenseur = etats[cote_attaquant], etats[not cote_attaquant]
        couloir = choisir_couloir(
            attaquant.notes.progression_attaque[zone], defenseur.notes.progression_defense[zone], cfg.moteur.couloirs, rng
        )
        return zone, couloir, False, None

    @staticmethod
    def _possession_suivante(resultat, etait_contre: bool, cfg: Config) -> tuple[Zone, Couloir, bool, Couloir | None]:
        # A contre that itself breaks down falls back to a deep restart,
        # not another contre. If it fell back to "the zone the ball was
        # lost in" instead, a turnover right next to goal would keep
        # re-triggering a "dangerous break" for whichever side just lost
        # it, forever — neither side's shot count would ever settle down.
        zone_declenchant_contre = Zone(cfg.moteur.turnover.zone_declenchant_contre)
        zones_avancees = {zone_declenchant_contre, Zone.VERITE}
        if resultat.zone_fin in zones_avancees:
            if not etait_contre:
                return zone_declenchant_contre, resultat.couloir_fin, True, resultat.couloir_fin
            return Zone.DEFENSE, resultat.couloir_fin, False, None
        return resultat.zone_fin, resultat.couloir_fin, False, None

    @staticmethod
    def _compter_tirs(etat: "_EtatCote", evenements: tuple[Evenement, ...], xg: float) -> None:
        for evenement in evenements:
            if evenement.type is TypeEvenement.TIR:
                etat.tirs += 1
                etat.xg += xg
                if evenement.detail == "corner":
                    etat.corners += 1

    @staticmethod
    def _enregistrer_carton(etat: "_EtatCote", fauteur: PositionOnze, couleur: str) -> str:
        """A direct red is "rouge_directe"; a second yellow for the same
        player in this match is an automatic "rouge_deuxieme_jaune" —
        docs/etats-joueur.md. The two carry different suspension lengths
        downstream (core/world/etats/suspensions.py), hence the distinct
        detail strings rather than just "rouge".
        """
        if couleur == "rouge":
            return "rouge_directe"
        compte = etat.jaunes_en_match.get(fauteur.joueur.id, 0) + 1
        etat.jaunes_en_match[fauteur.joueur.id] = compte
        return "rouge_deuxieme_jaune" if compte >= 2 else "jaune"

    @staticmethod
    def _calculer_notes(
        evenements: list[Evenement],
        onze_dom: tuple[PositionOnze, ...],
        onze_ext: tuple[PositionOnze, ...],
        cfg: Config,
    ) -> dict[int, float]:
        """No rating formula is given in docs/moteur-match.md — this
        starts every player at `etats.forme.note_reference` (the same
        "neutral" point forme's own formula centers on) and applies the
        adjustments in config/moteur_match.json -> note_match. An assist
        is credited to the TIR event's joueur_secondaire_id immediately
        preceding a BUT event (the crosser, for a headed goal).
        """
        cfg_note = cfg.moteur.note_match
        ajustements: dict[int, float] = {}

        def ajouter(joueur_id: int, valeur: float) -> None:
            ajustements[joueur_id] = ajustements.get(joueur_id, 0.0) + valeur

        for index, evenement in enumerate(evenements):
            if evenement.type is TypeEvenement.BUT:
                ajouter(evenement.joueur_id, cfg_note.bonus_but)
                precedent = evenements[index - 1] if index > 0 else None
                if (
                    precedent is not None
                    and precedent.type is TypeEvenement.TIR
                    and precedent.joueur_secondaire_id is not None
                ):
                    ajouter(precedent.joueur_secondaire_id, cfg_note.bonus_passe_decisive)
            elif evenement.type is TypeEvenement.CARTON:
                if evenement.detail == "jaune":
                    ajouter(evenement.joueur_id, cfg_note.malus_carton_jaune)
                else:
                    ajouter(evenement.joueur_id, cfg_note.malus_carton_rouge)

        tous_les_joueurs = {position.joueur.id for position in onze_dom} | {
            position.joueur.id for position in onze_ext
        }
        reference = cfg.etats.forme.note_reference
        return {
            joueur_id: min(max(reference + ajustements.get(joueur_id, 0.0), cfg_note.note_min), cfg_note.note_max)
            for joueur_id in tous_les_joueurs
        }

    @staticmethod
    def _evaluer_remplacement(
        etat: "_EtatCote",
        cote: bool,
        minute: int,
        buts: dict[bool, int],
        controleur: ClubController,
        tables,
        cfg: Config,
        evenements: list[Evenement],
    ) -> None:
        """Called once per possession; only actually consults the
        controller at the configured checkpoints (dedup via
        `derniere_minute_evaluee`, since several possessions can share a
        minute) — "évalué chaque intervalle_evaluation_minutes" per
        docs/etats-joueur.md.
        """
        cfg_r = cfg.etats.remplacements
        if minute < cfg_r.premiere_minute_evaluation or minute == etat.derniere_minute_evaluee:
            return
        if (minute - cfg_r.premiere_minute_evaluation) % cfg_r.intervalle_evaluation_minutes != 0:
            return
        etat.derniere_minute_evaluee = minute

        etat_match = EtatMatch(
            minute=minute,
            buts_pour=buts[cote],
            buts_contre=buts[not cote],
            onze_actuel=tuple(position.joueur for position in etat.equipe.onze),
            banc=tuple(etat.banc),
            remplacements_effectues=etat.remplacements_effectues,
        )
        decision = controleur.decider_remplacement(
            etat_match, frozenset(etat.jaunes_en_match), cfg.monde.regles_match.remplacements_max, cfg
        )
        if decision is None:
            return

        entrant = next((joueur for joueur in etat.banc if joueur.id == decision.joueur_entrant_id), None)
        if entrant is None:
            return
        onze = tuple(
            PositionOnze(poste=position.poste, joueur=entrant)
            if position.joueur.id == decision.joueur_sortant_id
            else position
            for position in etat.equipe.onze
        )
        if onze == etat.equipe.onze:
            return

        etat.banc = [joueur for joueur in etat.banc if joueur.id != entrant.id]
        etat.remplacements_effectues += 1
        etat.equipe = Equipe(
            club_id=etat.equipe.club_id,
            force_attaque=etat.equipe.force_attaque,
            force_defense=etat.equipe.force_defense,
            onze=onze,
            formation=etat.equipe.formation,
            hauteur_bloc=etat.equipe.hauteur_bloc,
        )
        etat.notes = calculer_notes_equipe(etat.equipe, tables, cfg)
        evenements.append(
            Evenement(
                minute, TypeEvenement.REMPLACEMENT, decision.joueur_entrant_id, decision.joueur_sortant_id, None, None,
                detail=decision.motif,
            )
        )

    @staticmethod
    def _expulser(etat: "_EtatCote", fauteur: PositionOnze, tables, cfg: Config) -> None:
        onze_reduit = tuple(position for position in etat.equipe.onze if position.joueur.id != fauteur.joueur.id)
        etat.equipe = Equipe(
            club_id=etat.equipe.club_id,
            force_attaque=etat.equipe.force_attaque,
            force_defense=etat.equipe.force_defense,
            onze=onze_reduit,
            formation=etat.equipe.formation,
            hauteur_bloc=etat.equipe.hauteur_bloc,
        )
        etat.notes = calculer_notes_equipe(etat.equipe, tables, cfg)

    @staticmethod
    def _stats(etat: "_EtatCote", adversaire: "_EtatCote") -> StatsEquipe:
        total_possessions = etat.possessions + adversaire.possessions
        possession_pct = 100.0 * etat.possessions / total_possessions if total_possessions else 50.0
        return StatsEquipe(
            tirs=etat.tirs,
            xg=round(etat.xg, 3),
            possession_pct=round(possession_pct, 1),
            corners=etat.corners,
            cartons_jaunes=etat.cartons_jaunes,
            cartons_rouges=etat.cartons_rouges,
        )
