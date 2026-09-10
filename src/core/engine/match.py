"""MoteurPossession: orchestrates a full match possession by possession.
See "Structure de la simulation" in docs/moteur-match.md.

Deliberately out of scope for this pass (documented, not silently
skipped): in-match fatigue/forme/moral evolution (forme/fatigue/moral
are read once, at kickoff, from each Joueur — the full dynamics belong
to step 6), player substitutions (need AIController.decider_remplacement,
step 7), injuries, and hauteur de bloc's effect on recovery zone /
vulnerability to the counter (accepted on Equipe, not yet consumed).
A red card still weakens a side for real: removing a player from onze
and recomputing notes_zones lets facteur_densite do the work, exactly
as docs prescribes — "aucun malus artificiel à ajouter" (the goalkeeper
is excluded from ever being sent off, see cartons.py — this model has
no way to put an outfield player in goal instead).
"""

from random import Random

from core.config.modeles.racine import Config
from core.domain.geometrie import Couloir, Zone
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

    def __init__(self, equipe: Equipe, notes: NotesEquipe) -> None:
        self.equipe = equipe
        self.notes = notes
        self.tirs = 0
        self.xg = 0.0
        self.corners = 0
        self.cartons_jaunes = 0
        self.cartons_rouges = 0
        self.possessions = 0


class MoteurPossession:
    def simuler(self, dom: Equipe, ext: Equipe, cfg: Config, rng: Random) -> ResultatMatch:
        tables = construire_tables_implication(cfg.implications)
        etats = {True: _EtatCote(dom, calculer_notes_equipe(dom, tables, cfg)), False: _EtatCote(ext, calculer_notes_equipe(ext, tables, cfg))}

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
                resultat.zone_fin, resultat.couloir_fin, defenseur.equipe.onze, tables, cfg.moteur.cartons, rng
            )
            if carton is not None:
                fauteur, couleur = carton
                evenements.append(
                    Evenement(minute, TypeEvenement.CARTON, fauteur.joueur.id, None, resultat.zone_fin, resultat.couloir_fin, detail=couleur)
                )
                if couleur == "rouge":
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
            notes={},
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
