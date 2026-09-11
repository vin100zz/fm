"""Day-by-day season orchestration — the piece every prior step
deferred ("rien n'appelle encore ces fonctions selon un calendrier").
See CLAUDE.md's `ClubController` note and "Contrôle du temps" in
docs/ui.md.

Scope for this pass: match simulation on schedule, standings, daily
fatigue recovery and injury rolls/healing, season-long suspension
countdown, and end-of-season rollover (`_relancer_saisons_terminees`) —
each competition gets its final table archived into
`Monde.historique.palmares` and a fresh fixture list the moment its own
calendrier is exhausted, independently of the others (Ligue 1's 18
clubs and La Liga's 20 don't finish the same day). **No promotion or
relegation**: the same `competition.club_ids` carry over forever — see
`Competition.appliquer_fin_saison` in docs/architecture.md, still not
built, and `docs/ui.md`.

Deliberately not here (documented, not silently skipped): mercato
windows and contract renewals (`docs/ia-gestion.md`'s own "hors
périmètre" note — no negotiation loop exists yet), monthly progression
(`core.world.progression.progresser` needs real per-player minutes
played this month, which nothing records yet — only match *ratings*
are tracked, not minutes), centre de formation promotion and the
démographie bilan (both dated in `config/monde.json -> dates_cles`, but
nothing triggers on a date here yet). Live in-match substitutions
aren't wired either: `AIController.choisir_composition` returns only
the onze, not the bench `MoteurPossession.simuler`'s optional `bancs`
parameter (step 7) needs.
"""

from random import Random

from core.ai.controller import AIController
from core.config.modeles.racine import Config
from core.domain.competition import Competition
from core.domain.historique import SaisonTerminee
from core.domain.journal import EvenementJour, TypeEvenementJour
from core.domain.match import Match
from core.domain.monde import Monde
from core.engine.match import MoteurPossession
from core.world import appliquer_match
from core.world.calendrier import generer_calendrier
from core.world.classement import calculer_classement
from core.world.etats import blessures, fatigue, suspensions

_CONTROLEUR = AIController()
_MOTEUR = MoteurPossession()


def matches_saison_courante(competition: Competition, monde: Monde) -> list[Match]:
    """The competition's current fixture list, as actually stored in
    `Monde.matches` — used by both the season loop and the read-side API
    (`api/routes_clubs.py`, `api/routes_competitions.py`) so a finished
    season's matches don't bleed into today's calendar/classement once
    `_relancer_saisons_terminees` has moved `saison_actuelle` on.
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


def _relancer_saisons_terminees(monde: Monde, cfg: Config, rng: Random) -> list[EvenementJour]:
    """A competition "ends" the moment every match of its current
    `saison` has a `resultat` — archives the final table, resets the
    season-long yellow-card count for its clubs' players, then
    generates the next edition's fixtures immediately (same
    `club_ids`: no promotion/relegation, see the module docstring).
    """
    journal: list[EvenementJour] = []

    for competition in monde.competitions.values():
        matches_saison = matches_saison_courante(competition, monde)
        if not matches_saison or any(match.resultat is None for match in matches_saison):
            continue

        classement = calculer_classement(competition.club_ids, matches_saison, cfg)
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
            competition.club_ids, competition.id, competition.saison_actuelle, monde.prochain_id, monde.date, cfg, rng
        )
        for match in nouveaux_matches:
            monde.matches[match.id] = match
        competition.calendrier = nouvelles_journees
        monde.prochain_id = max((match.id for match in nouveaux_matches), default=monde.prochain_id - 1) + 1

    if journal:
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
    journal += _relancer_saisons_terminees(monde, cfg, rng)
    return journal


def avancer_jusqua_journee(monde: Monde, cfg: Config, rng: Random, limite_jours: int = 30) -> list[EvenementJour]:
    """Ticks days until at least one match was played somewhere, or
    `limite_jours` is reached (every competition's calendar exhausted —
    otherwise this would loop forever).
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
