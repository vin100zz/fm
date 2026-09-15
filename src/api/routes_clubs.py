"""GET /api/clubs/* — "Club" screen in docs/ui.md.

Effectif, Calendrier, Transferts, Budget and the header are built.
Historique (past standings for a dormant-adjacent club) still needs data
nothing tracks yet — deferred, not stubbed.

Budget (2026-09-12, added, explicit user instruction) reuses the club
snapshot already on `VueClubDetail` (`budget_transfert`, `masse_salariale`,
`masse_salariale_max`, `solde` — no new endpoint needed for that part)
plus the new `mouvements-effectif`/`historique-financier` below for the
Transferts tab's three new sections and the Budget tab's financial
history.
"""

from fastapi import APIRouter, Depends, HTTPException

from api.etat_serveur import EtatServeur, obtenir_etat
from api.pagination import Page, paginer
from api.vues import (
    VueClubDetail,
    VueClubResume,
    VueJoueurLigne,
    VueMatchResume,
    VueMouvementEffectif,
    VueMouvementFinancier,
    VueTransfert,
    vue_club_detail,
    vue_club_resume,
    vue_joueur_ligne,
    vue_match_resume,
    vue_mouvement_effectif,
    vue_mouvement_financier,
    vue_mouvement_financier_transfert,
    vue_transfert,
)
from core.ai.budgets import effectifs_par_club, masse_salariale_actuelle
from core.domain.club import Club
from core.world.classement import calculer_classement
from core.world.saison import matches_saison_courante

routeur = APIRouter()


class VueTransfertClub(VueTransfert):
    sens: str  # "arrivee" | "depart", relatif au club consulte


@routeur.get("", response_model=Page[VueClubResume])
def lister_clubs(
    competition: int | None = None,
    statut: str | None = None,
    recherche: str | None = None,
    tri: str = "nom",
    page: int = 1,
    etat_serveur: EtatServeur = Depends(obtenir_etat),
) -> Page[VueClubResume]:
    clubs = list(etat_serveur.monde.clubs.values())
    if competition is not None:
        clubs = [c for c in clubs if c.competition_id == competition]
    if statut is not None:
        clubs = [c for c in clubs if c.statut.value == statut]
    if recherche:
        aiguille = recherche.lower()
        clubs = [c for c in clubs if aiguille in c.nom.lower()]

    if tri == "reputation":
        clubs.sort(key=lambda c: c.reputation, reverse=True)
    else:
        clubs.sort(key=lambda c: c.nom)

    nb_par_club, masse_par_club = effectifs_par_club(etat_serveur.monde.joueurs.values())
    return paginer(
        [vue_club_resume(c, nb_par_club.get(c.id, 0), masse_par_club.get(c.id, 0)) for c in clubs], page
    )


@routeur.get("/{club_id}", response_model=VueClubDetail)
def detail_club(club_id: int, etat_serveur: EtatServeur = Depends(obtenir_etat)) -> VueClubDetail:
    club = _recuperer_club(club_id, etat_serveur)
    classement = None
    competition = etat_serveur.monde.competitions.get(club.competition_id)
    if competition is not None:
        matches_saison = matches_saison_courante(competition, etat_serveur.monde)
        classement = calculer_classement(competition.club_ids, matches_saison, etat_serveur.cfg)
    effectif = [j for j in etat_serveur.monde.joueurs.values() if j.club_id == club_id]
    nb_joueurs_sous_contrat = sum(1 for j in effectif if j.contrat is not None)
    return vue_club_detail(
        club, classement, _forme_recente(club_id, etat_serveur),
        nb_joueurs_sous_contrat, masse_salariale_actuelle(effectif),
    )


@routeur.get("/{club_id}/effectif", response_model=list[VueJoueurLigne])
def effectif_club(club_id: int, etat_serveur: EtatServeur = Depends(obtenir_etat)) -> list[VueJoueurLigne]:
    club = _recuperer_club(club_id, etat_serveur)
    joueurs = sorted(
        (j for j in etat_serveur.monde.joueurs.values() if j.club_id == club_id), key=lambda j: j.poste.value
    )
    return [vue_joueur_ligne(joueur, etat_serveur.monde.date, etat_serveur.cfg, club) for joueur in joueurs]


@routeur.get("/{club_id}/calendrier", response_model=list[VueMatchResume])
def calendrier_club(club_id: int, etat_serveur: EtatServeur = Depends(obtenir_etat)) -> list[VueMatchResume]:
    club = _recuperer_club(club_id, etat_serveur)
    monde = etat_serveur.monde
    competition = monde.competitions.get(club.competition_id)
    matches_du_club = matches_saison_courante(competition, monde) if competition is not None else []
    matches = sorted(
        (m for m in matches_du_club if m.domicile_id == club_id or m.exterieur_id == club_id),
        key=lambda m: m.journee,
    )
    return [vue_match_resume(m, monde.clubs[m.domicile_id], monde.clubs[m.exterieur_id]) for m in matches]


@routeur.get("/{club_id}/transferts", response_model=list[VueTransfertClub])
def transferts_club(
    club_id: int, saison: int | None = None, etat_serveur: EtatServeur = Depends(obtenir_etat)
) -> list[VueTransfertClub]:
    _recuperer_club(club_id, etat_serveur)
    monde = etat_serveur.monde

    transferts = [
        t for t in monde.historique.transferts
        if club_id in (t.club_source_id, t.club_cible_id) and (saison is None or t.saison == saison)
    ]
    transferts.sort(key=lambda t: t.date, reverse=True)

    return [
        VueTransfertClub(
            **vue_transfert(t, monde).model_dump(),
            sens="arrivee" if t.club_cible_id == club_id else "depart",
        )
        for t in transferts
    ]


@routeur.get("/{club_id}/mouvements-effectif", response_model=list[VueMouvementEffectif])
def mouvements_effectif_club(
    club_id: int, type: str | None = None, etat_serveur: EtatServeur = Depends(obtenir_etat)
) -> list[VueMouvementEffectif]:
    """Departs libres en fin de contrat, retraites, promotions du centre
    de formation — sections de l'onglet "Transferts" distinctes des
    arrivees/departs payants (`/transferts`)."""
    _recuperer_club(club_id, etat_serveur)
    mouvements = [
        m for m in etat_serveur.monde.historique.mouvements_effectif
        if m.club_id == club_id and (type is None or m.type.value == type)
    ]
    mouvements.sort(key=lambda m: m.date, reverse=True)
    return [vue_mouvement_effectif(m) for m in mouvements]


@routeur.get("/{club_id}/historique-financier", response_model=list[VueMouvementFinancier])
def historique_financier_club(club_id: int, etat_serveur: EtatServeur = Depends(obtenir_etat)) -> list[VueMouvementFinancier]:
    """Revenus mensuels, salaires, primes de classement (`Historique.
    mouvements_financiers`) et transferts (`Historique.transferts`,
    deja la source de verite — pas duplique) fusionnes sur une seule
    ligne de temps pour l'onglet Budget."""
    _recuperer_club(club_id, etat_serveur)
    monde = etat_serveur.monde

    lignes = [
        (m.date, vue_mouvement_financier(m))
        for m in monde.historique.mouvements_financiers
        if m.club_id == club_id
    ]
    lignes += [
        (t.date, vue_mouvement_financier_transfert(t, monde, club_id))
        for t in monde.historique.transferts
        if club_id in (t.club_source_id, t.club_cible_id)
    ]
    lignes.sort(key=lambda paire: paire[0], reverse=True)
    return [vue for _, vue in lignes]


def _recuperer_club(club_id: int, etat_serveur: EtatServeur) -> Club:
    club = etat_serveur.monde.clubs.get(club_id)
    if club is None:
        raise HTTPException(status_code=404, detail="Club introuvable")
    return club


def _forme_recente(club_id: int, etat_serveur: EtatServeur, n: int = 5) -> list[str]:
    monde = etat_serveur.monde
    joues = sorted(
        (m for m in monde.matches.values() if (m.domicile_id == club_id or m.exterieur_id == club_id) and m.resultat is not None),
        key=lambda m: m.date,
    )
    forme = []
    for match in joues[-n:]:
        domicile = match.domicile_id == club_id
        buts_pour = match.resultat.buts_dom if domicile else match.resultat.buts_ext
        buts_contre = match.resultat.buts_ext if domicile else match.resultat.buts_dom
        forme.append("V" if buts_pour > buts_contre else "N" if buts_pour == buts_contre else "D")
    return forme
