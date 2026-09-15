"""Contract lifecycle for active clubs' squads — renewal decisions and
the annual release to free agency. See "Contrats et renouvellements"
in docs/ia-gestion.md.

**Simplified from docs/ia-gestion.md §6's three-way outcome** ("le club
renouvelle, met le joueur sur liste de transfert, ou le laisse partir
libre à échéance") **to the two-way version actually asked for**
(2026-09-11, explicit instruction): a club either renews, or does
nothing and the contract simply runs its course — no explicit
transfer-listing state. An unrenewed player keeps playing for their
current club until `date_fin`, then becomes a free agent
(`club_id = None`, `contrat = None`), signable by any active club —
see `core/world/mercato.py`'s free-agent branch for the buying side.

**All contracts this module or `core/world/mercato.py` create end on
`config/monde.json -> dates_cles.liberation_contrats_expires`
(30 juin)** — an explicit user convention, not something the source
data or docs impose. A contract's *length* in years still comes from
`duree_par_age`; only where it lands within the year is fixed, same as
real football almost always pins deals to a end-of-season date
regardless of the exact signing day. Imported contracts (real CSV
dates, `core/world/importation/construction.py`) are left as-is —
retroactively rewriting them would touch data fidelity, a different
concern; `liberer_contrats_expires` releases them correctly regardless
of their exact historical end date (`date_fin <= monde.date`, not an
exact match), so nothing but new contracts actually needs to land on
30 juin for the mechanism to work.

**Checked monthly, not weekly (2026-09-11, performance)**: docs says
"évalué chaque semaine", but `decision_renouvellement`'s expensive path
(`utilite()`, a `meilleure_affectation` call — the one thing
core/world/mercato.py's own docstring measured as the dominant cost in
this codebase) triggers for every player within
`mois_avant_fin_declenchant` (12 months) of their contract's end, which
at any moment is a large fraction of an active-club squad. Re-deciding
an unrenewed player daily for up to a year would repeat that expensive
call for nothing (the decision is stateless: it depends only on the
player/club/date, not on any record of when it was last asked) —
checking once a month instead is 30x cheaper and still comfortably
inside the 12-month window before a contract lapses.
"""

from core.ai.contrats import decision_renouvellement
from core.config.modeles.racine import Config
from core.domain.club import StatutClub
from core.domain.contrat import Contrat
from core.domain.date import Date
from core.domain.historique import MouvementEffectif, TypeMouvementEffectif
from core.domain.journal import EvenementJour, TypeEvenementJour
from core.domain.joueur import Joueur
from core.domain.monde import Monde


def renouveler_contrats(monde: Monde, cfg: Config) -> list[EvenementJour]:
    if monde.date.jour != 1:
        return []

    journal: list[EvenementJour] = []
    effectifs_par_club: dict[int, list[Joueur]] = {}
    for joueur in monde.joueurs.values():
        if joueur.club_id is not None:
            effectifs_par_club.setdefault(joueur.club_id, []).append(joueur)

    for club in monde.clubs.values():
        if club.statut is not StatutClub.ACTIF:
            continue
        effectif = effectifs_par_club.get(club.id, [])
        for joueur in effectif:
            if joueur.contrat is None:
                continue
            # utilite() compare "avec ce joueur" a "sans" — l'effectif
            # passe doit donc l'exclure, sinon "avec" et "sans" sont
            # quasi identiques (le joueur y figure deja) et le gain
            # marginal ressort a ~0 quel que soit son apport reel.
            effectif_sans_lui = [autre for autre in effectif if autre.id != joueur.id]
            decision = decision_renouvellement(joueur, club, effectif_sans_lui, 0.0, 0.0, monde.date, cfg)
            if not decision.renouvelle:
                continue

            dc = cfg.monde.dates_cles.liberation_contrats_expires
            joueur.contrat = Contrat(
                salaire_hebdo=decision.salaire_demande,
                date_fin=Date(monde.date.annee + decision.duree_annees, dc.mois, dc.jour),
                date_signature=monde.date,
            )
            journal.append(
                EvenementJour(
                    TypeEvenementJour.RENOUVELLEMENT,
                    f"{joueur.prenom} {joueur.nom} prolonge avec {club.nom}",
                    joueur_id=joueur.id,
                )
            )
    return journal


def liberer_contrats_expires(monde: Monde, cfg: Config) -> list[EvenementJour]:
    """1er juillet : tout joueur d'un club actif dont le contrat est
    arrivé à échéance (`date_fin <= monde.date` — pas une correspondance
    exacte, pour couvrir aussi les dates réelles importées qui ne tombent
    pas forcément un 30 juin) devient agent libre. Un joueur que son club
    a renouvelé entre-temps a déjà un `date_fin` repoussé de plusieurs
    années par `renouveler_contrats` et n'est donc jamais concerné ici —
    aucun état à suivre séparément pour "ce joueur a été gardé".
    """
    if not (monde.date.mois == 7 and monde.date.jour == 1):
        return []

    journal: list[EvenementJour] = []
    for joueur in monde.joueurs.values():
        if joueur.club_id is None or joueur.contrat is None:
            continue
        club = monde.clubs.get(joueur.club_id)
        if club is None or club.statut is not StatutClub.ACTIF:
            continue
        if joueur.contrat.date_fin > monde.date:
            continue

        journal.append(
            EvenementJour(
                TypeEvenementJour.AGENT_LIBRE,
                f"{joueur.prenom} {joueur.nom} est libre de tout contrat ({club.nom})",
                joueur_id=joueur.id,
            )
        )
        monde.historique.mouvements_effectif.append(
            MouvementEffectif(
                TypeMouvementEffectif.FIN_CONTRAT, monde.date, joueur.id, joueur.nom, joueur.prenom, club.id, monde.saison
            )
        )
        joueur.club_id = None
        joueur.contrat = None
    return journal
