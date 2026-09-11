"""Day-by-day season orchestration — the piece every prior step
deferred ("rien n'appelle encore ces fonctions selon un calendrier").
See CLAUDE.md's `ClubController` note and "Contrôle du temps" in
docs/ui.md.

Scope for this pass: match simulation on schedule, standings, daily
fatigue recovery and injury rolls/healing, season-long suspension
countdown, end-of-season rollover (`_relancer_saison_au_1er_juillet`)
— one season per calendar year, 1st July to 30th June, per explicit
user instruction: every competition's final table is archived into
`Monde.historique.palmares` and every competition gets a fresh fixture
list **together**, the moment `monde.date` crosses 1st July — not
independently whenever each one's own calendrier happens to run out
(Ligue 1's 18 clubs and La Liga's 20 finish playing at different points
in April/May either way, since the fixture spacing alone determines
that; the *administrative* season boundary is now the same calendar
date for all five). The new fixture list itself doesn't start the next
day — its first match is scheduled at `config/monde.json ->
saison.debut_mois/jour` (mid-August) of that same year, leaving the
close season gap `docs/ia-gestion.md`'s mercato window sits inside.
Also as of this pass: the transfer window itself
(`core.world.mercato.avancer_mercato`, called whenever `monde.date`
falls inside `config/monde.json -> mercato.ete/hiver`). **No promotion
or relegation**: the same `competition.club_ids` carry over forever —
see `Competition.appliquer_fin_saison` in docs/architecture.md, still
not built, and `docs/ui.md`.

Deliberately not here (documented, not silently skipped): weekly
contract renewals and free agency (`core.ai.contrats.decision_renouvellement`
exists, nothing calls it — see `core/world/mercato.py`'s own docstring),
monthly progression (`core.world.progression.progresser` needs real
per-player minutes played this month, which nothing records yet — only
match *ratings* are tracked, not minutes), centre de formation
promotion and the démographie bilan (both dated in `config/monde.json
-> dates_cles`, but nothing triggers on a date here yet). Live in-match
substitutions aren't wired either: `AIController.choisir_composition`
returns only the onze, not the bench `MoteurPossession.simuler`'s
optional `bancs` parameter (step 7) needs.
"""

from random import Random

from core.ai.controller import AIController
from core.config.modeles.racine import Config
from core.domain.competition import Competition
from core.domain.date import Date
from core.domain.historique import SaisonTerminee
from core.domain.journal import EvenementJour, TypeEvenementJour
from core.domain.match import Match
from core.domain.monde import Monde
from core.engine.match import MoteurPossession
from core.world import appliquer_match
from core.world.calendrier import generer_calendrier
from core.world.classement import calculer_classement
from core.world.etats import blessures, fatigue, suspensions
from core.world.mercato import avancer_mercato

_CONTROLEUR = AIController()
_MOTEUR = MoteurPossession()


def matches_saison_courante(competition: Competition, monde: Monde) -> list[Match]:
    """The competition's current fixture list, as actually stored in
    `Monde.matches` — used by both the season loop and the read-side API
    (`api/routes_clubs.py`, `api/routes_competitions.py`) so a finished
    season's matches don't bleed into today's calendar/classement once
    `_relancer_saison_au_1er_juillet` has moved `saison_actuelle` on.
    """
    return [
        match for match in monde.matches.values()
        if match.competition_id == competition.id and match.saison == competition.saison_actuelle
    ]


def initialiser_saison(monde: Monde, cfg: Config, rng: Random) -> None:
    """Generates each competition's fixture list once — a no-op for a
    competition that already has one (mid-season reload, or a second
    call by mistake).
    """
    for competition in monde.competitions.values():
        if competition.calendrier:
            continue
        matches, journees = generer_calendrier(
            competition.club_ids, competition.id, competition.saison_actuelle, monde.prochain_id, monde.date, cfg, rng
        )
        for match in matches:
            monde.matches[match.id] = match
        competition.calendrier = journees
        monde.prochain_id = max((match.id for match in matches), default=monde.prochain_id - 1) + 1


def _relancer_saison_au_1er_juillet(monde: Monde, cfg: Config, rng: Random) -> list[EvenementJour]:
    """One season a year, 1st July to 30th June (explicit user
    instruction, 2026-09-11) — every competition rolls over **together**
    on this one date, not independently whenever its own calendrier
    happens to be exhausted (see the module docstring). Archives
    whichever matches were actually played this season, even if that
    isn't all of them: with the configured fixture spacing a season's
    matches always finish around April/May, well before the next 1st
    July, but archiving on whatever was played rather than demanding
    every match have a `resultat` is the more robust rule — an
    abandoned/short season should still close out, not stall forever.
    """
    if not (monde.date.mois == 7 and monde.date.jour == 1):
        return []

    journal: list[EvenementJour] = []
    date_debut_prochaine = Date(monde.date.annee, cfg.monde.saison.debut_mois, cfg.monde.saison.debut_jour)

    for competition in monde.competitions.values():
        matches_joues = [m for m in matches_saison_courante(competition, monde) if m.resultat is not None]
        if matches_joues:
            classement = calculer_classement(competition.club_ids, matches_joues, cfg)
            monde.historique.palmares.append(
                SaisonTerminee(competition_id=competition.id, saison=competition.saison_actuelle, classement_final=classement)
            )
            champion = monde.clubs[classement[0].club_id]
            journal.append(
                EvenementJour(
                    TypeEvenementJour.FIN_DE_SAISON, f"{champion.nom} est champion de {competition.nom} !",
                    competition_id=competition.id,
                )
            )

        for joueur in monde.joueurs.values():
            if joueur.club_id in competition.club_ids:
                suspensions.reinitialiser_saison(joueur, cfg.etats.suspensions)

        competition.saison_actuelle += 1
        nouveaux_matches, nouvelles_journees = generer_calendrier(
            competition.club_ids, competition.id, competition.saison_actuelle, monde.prochain_id, date_debut_prochaine, cfg, rng
        )
        for match in nouveaux_matches:
            monde.matches[match.id] = match
        competition.calendrier = nouvelles_journees
        monde.prochain_id = max((match.id for match in nouveaux_matches), default=monde.prochain_id - 1) + 1

    monde.saison = max(competition.saison_actuelle for competition in monde.competitions.values())
    return journal


def avancer_un_jour(monde: Monde, cfg: Config, rng: Random) -> list[EvenementJour]:
    journal: list[EvenementJour] = []
    ont_joue: set[int] = set()

    for match in _matches_du_jour(monde):
        journal.append(_jouer_match(match, monde, cfg, rng))
        ont_joue |= set(match.resultat.notes)

    for joueur in monde.joueurs.values():
        if joueur.club_id is None:
            continue
        if joueur.id not in ont_joue:
            fatigue.recuperer(joueur, 1.0, monde.date, cfg.etats.fatigue)

        if joueur.blessure is not None and monde.date >= joueur.blessure.date_fin:
            blessures.retablir(joueur, cfg, rng)
        elif joueur.blessure is None:
            if blessures.evaluer_blessure_hors_match(joueur, monde.date, cfg.etats.blessures, rng):
                journal.append(EvenementJour(TypeEvenementJour.BLESSURE, f"{joueur.prenom} {joueur.nom} est blessé", joueur_id=joueur.id))

    monde.date = monde.date.plus_jours(1)
    journal += avancer_mercato(monde, cfg, rng)
    journal += _relancer_saison_au_1er_juillet(monde, cfg, rng)
    return journal


def avancer_jusqua_journee(monde: Monde, cfg: Config, rng: Random, limite_jours: int = 120) -> list[EvenementJour]:
    """Ticks days until at least one match was played somewhere, or
    `limite_jours` is reached. Needed even outside a truly indefinite
    gap: the close season between a competition's last match (~April/May
    with the configured fixture spacing) and the next one's kickoff
    (mid-August, `_relancer_saison_au_1er_juillet`) is itself ~100 days
    with nothing to play — `limite_jours` defaults comfortably above
    that so one call still reaches the next real matchday.
    """
    journal: list[EvenementJour] = []
    for _ in range(limite_jours):
        journal_du_jour = avancer_un_jour(monde, cfg, rng)
        journal.extend(journal_du_jour)
        if any(evenement.type is TypeEvenementJour.RESULTAT for evenement in journal_du_jour):
            break
    return journal


def _matches_du_jour(monde: Monde) -> list[Match]:
    return [match for match in monde.matches.values() if match.date == monde.date and match.resultat is None]


def _jouer_match(match: Match, monde: Monde, cfg: Config, rng: Random) -> EvenementJour:
    club_dom, club_ext = monde.clubs[match.domicile_id], monde.clubs[match.exterieur_id]
    effectif_dom = [j for j in monde.joueurs.values() if j.club_id == club_dom.id]
    effectif_ext = [j for j in monde.joueurs.values() if j.club_id == club_ext.id]

    equipe_dom = _CONTROLEUR.choisir_composition(club_dom, effectif_dom, club_ext, domicile=True, cfg=cfg)
    equipe_ext = _CONTROLEUR.choisir_composition(club_ext, effectif_ext, club_dom, domicile=False, cfg=cfg)

    resultat = _MOTEUR.simuler(equipe_dom, equipe_ext, cfg, rng)
    match.resultat = resultat
    appliquer_match.appliquer_resultat_match(resultat, monde.joueurs, cfg, rng)

    for joueur in effectif_dom + effectif_ext:
        suspensions.decrementer(joueur)

    description = f"{club_dom.nom} {resultat.buts_dom} - {resultat.buts_ext} {club_ext.nom}"
    return EvenementJour(TypeEvenementJour.RESULTAT, description, match_id=match.id)
