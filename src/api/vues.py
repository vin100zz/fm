"""View models and their mappers — "penser en vues, pas en entités"
(docs/ui.md): each function here returns exactly what one screen shows,
not a generic serialization of a domain entity.
"""

from pydantic import BaseModel

from core.ai.valorisation import estimation_potentiel, valeur
from core.config.modeles.racine import Config
from core.domain.classement import LigneClassement
from core.domain.club import Club, StatutClub
from core.domain.date import Date
from core.domain.historique import TransfertHistorique
from core.domain.joueur import Joueur
from core.domain.match import Match
from core.domain.monde import Monde
from core.world.note_globale import note_globale


class VueClubResume(BaseModel):
    id: int
    nom: str
    pays: str
    statut: str
    competition_id: int | None
    reputation: int
    nb_joueurs_sous_contrat: int
    masse_salariale: int
    budget_transfert: int


class VueClubDetail(VueClubResume):
    note_centre_formation: int
    masse_salariale_max: int
    solde: int
    formation_preferee: str
    classement_actuel: int | None
    forme_recente: list[str]  # "V"/"N"/"D", le plus recent en dernier


class VueEtatJoueur(BaseModel):
    blesse: bool
    jours_indisponibilite_restants: int | None
    suspendu: bool
    matches_suspension_restants: int | None
    fatigue: float
    forme: float
    moral: float


class VueJoueurLigne(BaseModel):
    """Une ligne de la liste "Effectif" ou de la recherche de joueurs —
    docs/ui.md : "trois chiffres par ligne de joueur : âge, salaire, fin
    de contrat", plus le strict nécessaire pour trier/filtrer côté client.
    """

    id: int
    nom: str
    prenom: str
    poste: str
    age: int
    niveau: float
    nationalite: str
    club_id: int | None
    club_nom: str | None
    statut_club: str | None
    salaire_hebdo: int | None
    date_fin_contrat: str | None
    echeance_proche: bool  # fin de contrat a moins de 12 mois
    etat: VueEtatJoueur


class VueFourchette(BaseModel):
    min: float
    max: float


class VueJoueurDetail(BaseModel):
    id: int
    nom: str
    prenom: str
    nationalite: str
    age: int
    date_naissance: str
    poste: str
    postes_secondaires: dict[str, float]
    attributs: dict[str, dict[str, int]]  # famille -> {attribut: valeur}
    niveau: float
    potentiel_estime: VueFourchette
    etat: VueEtatJoueur
    club_id: int | None
    club_nom: str | None
    salaire_hebdo: int | None
    date_fin_contrat: str | None
    valeur_estimee: int


class VueCompetitionResume(BaseModel):
    id: int
    nom: str
    pays: str
    niveau: int
    nb_clubs: int


class VueLigneClassement(BaseModel):
    rang: int
    club_id: int
    club_nom: str
    joues: int
    victoires: int
    nuls: int
    defaites: int
    buts_pour: int
    buts_contre: int
    difference_buts: int
    points: int


class VueMatchResume(BaseModel):
    id: int
    journee: int
    date: str
    domicile_id: int
    domicile_nom: str
    exterieur_id: int
    exterieur_nom: str
    joue: bool
    buts_dom: int | None
    buts_ext: int | None


class VueTransfert(BaseModel):
    date: str
    joueur_id: int
    joueur_nom: str
    club_source_id: int | None
    club_source_nom: str | None
    club_cible_id: int | None
    club_cible_nom: str | None
    montant: int
    saison: int


FAMILLES_ATTRIBUTS: dict[str, list[str]] = {
    "techniques": ["passe", "technique", "finition", "tacle", "jeu_tete"],
    "mentaux": ["vision", "placement", "sang_froid"],
    "physiques": ["vitesse", "endurance"],
    "gardien": ["reflexes", "sorties", "relance"],
}


def vue_club_resume(club: Club, nb_joueurs_sous_contrat: int, masse_salariale: int) -> VueClubResume:
    """`Club.competition_id` holds the source data's raw division id for
    every club, active or dormant (not a -1 sentinel) — only a club
    whose `statut` is ACTIF has one of the 5 simulated competitions
    behind it, so that's what gates whether to expose it.

    `nb_joueurs_sous_contrat`/`masse_salariale` aren't on `Club` itself
    (the squad lives in `Monde.joueurs`, keyed globally) — the caller
    aggregates them, efficiently, from there (`core.ai.budgets`).
    """
    return VueClubResume(
        id=club.id, nom=club.nom, pays=club.pays, statut=club.statut.value,
        competition_id=club.competition_id if club.statut is StatutClub.ACTIF else None,
        reputation=club.reputation, nb_joueurs_sous_contrat=nb_joueurs_sous_contrat,
        masse_salariale=masse_salariale, budget_transfert=club.budget_transfert,
    )


def vue_club_detail(
    club: Club, classement: list[LigneClassement] | None, forme_recente: list[str],
    nb_joueurs_sous_contrat: int, masse_salariale: int,
) -> VueClubDetail:
    rang = None
    if classement is not None:
        for position, ligne in enumerate(classement, start=1):
            if ligne.club_id == club.id:
                rang = position
                break
    return VueClubDetail(
        **vue_club_resume(club, nb_joueurs_sous_contrat, masse_salariale).model_dump(),
        note_centre_formation=club.note_centre_formation,
        masse_salariale_max=club.masse_salariale_max, solde=club.solde, formation_preferee=club.formation_preferee,
        classement_actuel=rang, forme_recente=forme_recente,
    )


def _etat_joueur(joueur: Joueur, date_actuelle: Date) -> VueEtatJoueur:
    jours_restants = max(date_actuelle.jours_jusqua(joueur.blessure.date_fin), 0) if joueur.blessure else None
    return VueEtatJoueur(
        blesse=joueur.blessure is not None,
        jours_indisponibilite_restants=jours_restants,
        suspendu=joueur.suspension is not None,
        matches_suspension_restants=joueur.suspension.matches_restants if joueur.suspension else None,
        fatigue=round(joueur.fatigue, 2), forme=round(joueur.forme, 2), moral=round(joueur.moral, 2),
    )


def vue_joueur_ligne(joueur: Joueur, date_actuelle: Date, cfg: Config, club: Club | None) -> VueJoueurLigne:
    echeance_proche = False
    date_fin = None
    if joueur.contrat is not None:
        date_fin = str(joueur.contrat.date_fin)
        echeance_proche = date_actuelle.jours_jusqua(joueur.contrat.date_fin) < 365

    return VueJoueurLigne(
        id=joueur.id, nom=joueur.nom, prenom=joueur.prenom, poste=joueur.poste.value,
        age=joueur.date_naissance.age_a(date_actuelle), niveau=round(note_globale(joueur, cfg.attributs), 1),
        nationalite=joueur.nationalite, club_id=joueur.club_id, club_nom=club.nom if club else None,
        statut_club=club.statut.value if club else None,
        salaire_hebdo=joueur.contrat.salaire_hebdo if joueur.contrat else None,
        date_fin_contrat=date_fin, echeance_proche=echeance_proche, etat=_etat_joueur(joueur, date_actuelle),
    )


def vue_joueur_detail(joueur: Joueur, date_actuelle: Date, cfg: Config, club: Club | None) -> VueJoueurDetail:
    attributs_par_famille = {
        famille: {nom: joueur.attributs.valeur(nom) for nom in noms} for famille, noms in FAMILLES_ATTRIBUTS.items()
    }
    fourchette = estimation_potentiel(joueur, date_actuelle, cfg, club_observateur=club)

    return VueJoueurDetail(
        id=joueur.id, nom=joueur.nom, prenom=joueur.prenom, nationalite=joueur.nationalite,
        age=joueur.date_naissance.age_a(date_actuelle), date_naissance=str(joueur.date_naissance),
        poste=joueur.poste.value, postes_secondaires={p.value: a for p, a in joueur.postes_secondaires.items()},
        attributs=attributs_par_famille, niveau=round(note_globale(joueur, cfg.attributs), 1),
        potentiel_estime=VueFourchette(min=round(fourchette.min, 1), max=round(fourchette.max, 1)),
        etat=_etat_joueur(joueur, date_actuelle), club_id=joueur.club_id, club_nom=club.nom if club else None,
        salaire_hebdo=joueur.contrat.salaire_hebdo if joueur.contrat else None,
        date_fin_contrat=str(joueur.contrat.date_fin) if joueur.contrat else None,
        valeur_estimee=valeur(joueur, date_actuelle, cfg),
    )


def vue_ligne_classement(ligne: LigneClassement, rang: int, club: Club) -> VueLigneClassement:
    return VueLigneClassement(
        rang=rang, club_id=ligne.club_id, club_nom=club.nom, joues=ligne.joues, victoires=ligne.victoires,
        nuls=ligne.nuls, defaites=ligne.defaites, buts_pour=ligne.buts_pour, buts_contre=ligne.buts_contre,
        difference_buts=ligne.difference_buts, points=ligne.points,
    )


def vue_transfert(transfert: TransfertHistorique, monde: Monde) -> VueTransfert:
    joueur = monde.joueurs.get(transfert.joueur_id)
    club_source = monde.clubs.get(transfert.club_source_id) if transfert.club_source_id is not None else None
    club_cible = monde.clubs.get(transfert.club_cible_id) if transfert.club_cible_id is not None else None
    return VueTransfert(
        date=str(transfert.date), joueur_id=transfert.joueur_id,
        joueur_nom=f"{joueur.prenom} {joueur.nom}".strip() if joueur else "?",
        club_source_id=transfert.club_source_id, club_source_nom=club_source.nom if club_source else None,
        club_cible_id=transfert.club_cible_id, club_cible_nom=club_cible.nom if club_cible else None,
        montant=transfert.montant, saison=transfert.saison,
    )


def vue_match_resume(match: Match, club_dom: Club, club_ext: Club) -> VueMatchResume:
    return VueMatchResume(
        id=match.id, journee=match.journee, date=str(match.date),
        domicile_id=match.domicile_id, domicile_nom=club_dom.nom, exterieur_id=match.exterieur_id, exterieur_nom=club_ext.nom,
        joue=match.resultat is not None,
        buts_dom=match.resultat.buts_dom if match.resultat else None,
        buts_ext=match.resultat.buts_ext if match.resultat else None,
    )
