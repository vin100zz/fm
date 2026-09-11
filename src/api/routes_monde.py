"""GET/POST /api/monde/* — "Contrôle du temps" in docs/ui.md.

`avancer` only supports `jusqu_a in {"jour", "journee"}`; "fin_mercato"
from docs isn't offered — there's no mercato loop yet to advance to the
end of (docs/ia-gestion.md's own "hors périmètre" note).
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.etat_serveur import EtatServeur, obtenir_etat
from core.domain.journal import EvenementJour
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
    return VueEtatMonde(date=str(monde.date), saison=monde.saison, prochaines_echeances=echeances)


@routeur.post("/avancer", response_model=ReponseAvancer)
def avancer(requete: RequeteAvancer, etat_serveur: EtatServeur = Depends(obtenir_etat)) -> ReponseAvancer:
    if requete.jusqu_a == "journee":
        journal = avancer_jusqua_journee(etat_serveur.monde, etat_serveur.cfg, etat_serveur.rng)
    else:
        journal = avancer_un_jour(etat_serveur.monde, etat_serveur.cfg, etat_serveur.rng)

    etat_serveur.dernier_journal = journal
    return ReponseAvancer(date=str(etat_serveur.monde.date), journal=[_vue_evenement(e) for e in journal])


@routeur.get("/journal", response_model=list[VueEvenementJour])
def journal(etat_serveur: EtatServeur = Depends(obtenir_etat)) -> list[VueEvenementJour]:
    """Renvoie le journal de la dernière avancée du temps — pas
    d'historique par date interrogeable, rien ne le persiste encore.
    """
    return [_vue_evenement(e) for e in etat_serveur.dernier_journal]
