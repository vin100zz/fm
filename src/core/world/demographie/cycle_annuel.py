"""Once-a-year player life-cycle events for active clubs' own squads:
retirement and academy promotion. See "Sorties" and "Centres de
formation" in docs/progression-demographie.md — both had been pure,
uncalled functions since step 8 ("rien n'appelle encore ces fonctions
selon un calendrier"); wired up here for the first time (2026-09-12,
explicit user instruction, needed to populate a club's Transferts tab
with real départs à la retraite / promus du centre de formation rather
than an empty section).

Checked once a year, at `config/monde.json -> dates_cles.promotion_centre_formation`
(15 juin) — the date docs/progression-demographie.md already names for
academy promotions, reused here for retirement too since both are
per-player/per-club annual life-cycle events with no finer-grained
trigger of their own, right before `liberer_contrats_expires` (30 juin)
and the season rollover (1er juillet).

**Deliberately narrower than the full démographie feedback loop**
(`core/world/demographie/cohorte.py`, the "boucle de rétroaction"
comparing observed population to target bucket by bucket) — that stays
unwired. This only makes retirement and academy promotion real events
for active clubs' own squads, the minimum needed for the Transferts tab
ask; rebalancing the wider ~32 000-player population is a separate,
larger piece of work.
"""

from random import Random

from core.config.modeles.racine import Config
from core.domain.club import StatutClub
from core.domain.historique import MouvementEffectif, TypeMouvementEffectif
from core.domain.journal import EvenementJour, TypeEvenementJour
from core.domain.monde import Monde
from core.world.demographie.generation import nationalites_simulees, promouvoir_centre_formation
from core.world.demographie.identite import construire_pools_noms
from core.world.demographie.sorties import probabilite_retraite


def appliquer_cycle_annuel_effectif(monde: Monde, cfg: Config, rng: Random) -> list[EvenementJour]:
    dc = cfg.monde.dates_cles.promotion_centre_formation
    if not (monde.date.mois == dc.mois and monde.date.jour == dc.jour):
        return []

    journal = _appliquer_retraites(monde, cfg, rng)
    journal += _appliquer_promotions(monde, cfg, rng)
    return journal


def _appliquer_retraites(monde: Monde, cfg: Config, rng: Random) -> list[EvenementJour]:
    journal: list[EvenementJour] = []
    # list(...) : on retire des entrees de monde.joueurs pendant l'iteration.
    for joueur in list(monde.joueurs.values()):
        if joueur.club_id is None:
            continue
        club = monde.clubs.get(joueur.club_id)
        if club is None or club.statut is not StatutClub.ACTIF:
            continue
        if rng.random() >= probabilite_retraite(joueur, monde.date, cfg):
            continue

        journal.append(
            EvenementJour(
                TypeEvenementJour.RETRAITE,
                f"{joueur.prenom} {joueur.nom} prend sa retraite ({club.nom})",
                joueur_id=joueur.id,
            )
        )
        monde.historique.mouvements_effectif.append(
            MouvementEffectif(
                TypeMouvementEffectif.RETRAITE, monde.date, joueur.id, joueur.nom, joueur.prenom, club.id, monde.saison
            )
        )
        del monde.joueurs[joueur.id]
    return journal


def _appliquer_promotions(monde: Monde, cfg: Config, rng: Random) -> list[EvenementJour]:
    journal: list[EvenementJour] = []
    pools = construire_pools_noms(monde.joueurs.values(), nationalites_simulees(cfg))
    deja_utilises = frozenset((j.nom, j.prenom) for j in monde.joueurs.values())

    for club in monde.clubs.values():
        if club.statut is not StatutClub.ACTIF:
            continue

        promus = promouvoir_centre_formation(club, monde.prochain_id, monde.date, pools, deja_utilises, cfg, rng)
        for joueur in promus:
            monde.joueurs[joueur.id] = joueur
            journal.append(
                EvenementJour(
                    TypeEvenementJour.PROMOTION,
                    f"{joueur.prenom} {joueur.nom} est promu du centre de formation ({club.nom})",
                    joueur_id=joueur.id,
                )
            )
            monde.historique.mouvements_effectif.append(
                MouvementEffectif(
                    TypeMouvementEffectif.PROMOTION, monde.date, joueur.id, joueur.nom, joueur.prenom, club.id, monde.saison
                )
            )
        if promus:
            monde.prochain_id += len(promus)
            deja_utilises = deja_utilises | {(j.nom, j.prenom) for j in promus}
    return journal
