"""GET/POST /api/monde/* — "Contrôle du temps" in docs/ui.md.

`avancer` only supports `jusqu_a in {"jour", "journee"}`; "fin_mercato"
still isn't offered — `avancer_mercato` (`core/world/mercato.py`) runs
automatically inside `avancer_un_jour` whenever the date falls in a
window, one turn per day, rather than being a distinct destination to
fast-forward to.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.etat_serveur import EtatServeur, obtenir_etat
from api.pagination import Page, paginer
from api.vues import VueTransfert, vue_transfert
from core.domain.journal import EvenementJour
from core.world.mercato import fenetre_mercato_ouverte
from core.world.saison import avancer_jusqua_journee, avancer_un_jour

routeur = APIRouter()


class VueEvenementJour(BaseModel):
    type: str
    description: str
    match_id: int | None
    joueur_id: int | None


class VueEtatMonde(BaseModel):
    date: str
    saison: int
    prochaines_echeances: dict[str, str]
    mercato_ouvert: bool


class RequeteAvancer(BaseModel):
    jusqu_a: str = "jour"


class ReponseAvancer(BaseModel):
    date: str
    journal: list[VueEvenementJour]


def _vue_evenement(evenement: EvenementJour) -> VueEvenementJour:
    return VueEvenementJour(
        type=evenement.type.value, description=evenement.description,
        match_id=evenement.match_id, joueur_id=evenement.joueur_id,
    )


@routeur.get("/etat", response_model=VueEtatMonde)
def etat(etat_serveur: EtatServeur = Depends(obtenir_etat)) -> VueEtatMonde:
    monde = etat_serveur.monde
    echeances: dict[str, str] = {}
    for competition in monde.competitions.values():
        dates_restantes = [m.date for m in monde.matches.values() if m.competition_id == competition.id and m.resultat is None]
        if dates_restantes:
            echeances[competition.nom] = str(min(dates_restantes))
    mercato_ouvert = fenetre_mercato_ouverte(monde.date, etat_serveur.cfg)
    return VueEtatMonde(date=str(monde.date), saison=monde.saison, prochaines_echeances=echeances, mercato_ouvert=mercato_ouvert)


@routeur.post("/avancer", response_model=ReponseAvancer)
def avancer(requete: RequeteAvancer, etat_serveur: EtatServeur = Depends(obtenir_etat)) -> ReponseAvancer:
    if requete.jusqu_a == "journee":
        journal = avancer_jusqua_journee(etat_serveur.monde, etat_serveur.cfg, etat_serveur.rng)
    else:
        journal = avancer_un_jour(etat_serveur.monde, etat_serveur.cfg, etat_serveur.rng)

    etat_serveur.dernier_journal = journal
    return ReponseAvancer(date=str(etat_serveur.monde.date), journal=[_vue_evenement(e) for e in journal])


@routeur.get("/transferts", response_model=Page[VueTransfert])
def transferts(
    saison: int | None = None, club: int | None = None, page: int = 1,
    etat_serveur: EtatServeur = Depends(obtenir_etat),
) -> Page[VueTransfert]:
    """Tous les transferts conclus, toutes saisons et tous clubs
    confondus (contrairement à `GET /api/clubs/{id}/transferts`, filtré
    sur un seul club) — écran "Transferts" du menu principal.
    """
    monde = etat_serveur.monde
    transferts_filtres = monde.historique.transferts
    if saison is not None:
        transferts_filtres = [t for t in transferts_filtres if t.saison == saison]
    if club is not None:
        transferts_filtres = [t for t in transferts_filtres if club in (t.club_source_id, t.club_cible_id)]
    transferts_filtres = sorted(transferts_filtres, key=lambda t: t.date, reverse=True)
    return paginer([vue_transfert(t, monde) for t in transferts_filtres], page)


@routeur.get("/journal", response_model=list[VueEvenementJour])
def journal(etat_serveur: EtatServeur = Depends(obtenir_etat)) -> list[VueEvenementJour]:
    """Renvoie le journal de la dernière avancée du temps — pas
    d'historique par date interrogeable, rien ne le persiste encore.
    """
    return [_vue_evenement(e) for e in etat_serveur.dernier_journal]
