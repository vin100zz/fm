"""GET /api/competitions/* — "Compétition" screen in docs/ui.md.

Classement, Calendrier and (partly) Historique are built. Statistiques
(buteurs, passeurs, notes moyennes) still need per-season stat
aggregation nothing tracks yet — matches are simulated with full
events, but nothing accumulates them across a season. Historique only
has champions and final tables (`Historique.palmares`,
`core/world/saison.py`): no top scorer/passer per season, same gap.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.etat_serveur import EtatServeur, obtenir_etat
from api.vues import VueCompetitionResume, VueLigneClassement, VueMatchResume, vue_ligne_classement, vue_match_resume
from core.domain.competition import Competition
from core.world.classement import calculer_classement
from core.world.saison import matches_saison_courante

routeur = APIRouter()


class VueSaisonTerminee(BaseModel):
    saison: int
    champion_id: int
    champion_nom: str
    classement_final: list[VueLigneClassement]


@routeur.get("", response_model=list[VueCompetitionResume])
def lister_competitions(etat_serveur: EtatServeur = Depends(obtenir_etat)) -> list[VueCompetitionResume]:
    return [
        VueCompetitionResume(id=c.id, nom=c.nom, pays=c.pays, niveau=c.niveau, nb_clubs=len(c.club_ids))
        for c in etat_serveur.monde.competitions.values()
    ]


@routeur.get("/{competition_id}/classement", response_model=list[VueLigneClassement])
def classement(competition_id: int, etat_serveur: EtatServeur = Depends(obtenir_etat)) -> list[VueLigneClassement]:
    competition = _recuperer_competition(competition_id, etat_serveur)
    monde = etat_serveur.monde
    matches_saison = matches_saison_courante(competition, monde)
    lignes = calculer_classement(competition.club_ids, matches_saison, etat_serveur.cfg)
    return [vue_ligne_classement(ligne, rang, monde.clubs[ligne.club_id]) for rang, ligne in enumerate(lignes, start=1)]


@routeur.get("/{competition_id}/calendrier", response_model=list[VueMatchResume])
def calendrier(
    competition_id: int, journee: int | None = None, etat_serveur: EtatServeur = Depends(obtenir_etat)
) -> list[VueMatchResume]:
    competition = _recuperer_competition(competition_id, etat_serveur)
    monde = etat_serveur.monde
    matches = _matches_saison_courante(competition, monde)
    if journee is not None:
        matches = [m for m in matches if m.journee == journee]
    matches.sort(key=lambda m: (m.journee, m.id))
    return [vue_match_resume(m, monde.clubs[m.domicile_id], monde.clubs[m.exterieur_id]) for m in matches]


@routeur.get("/{competition_id}/historique", response_model=list[VueSaisonTerminee])
def historique(competition_id: int, etat_serveur: EtatServeur = Depends(obtenir_etat)) -> list[VueSaisonTerminee]:
    _recuperer_competition(competition_id, etat_serveur)
    monde = etat_serveur.monde
    saisons = [s for s in monde.historique.palmares if s.competition_id == competition_id]
    saisons.sort(key=lambda s: s.saison, reverse=True)
    return [
        VueSaisonTerminee(
            saison=saison.saison, champion_id=saison.champion_id, champion_nom=monde.clubs[saison.champion_id].nom,
            classement_final=[
                vue_ligne_classement(ligne, rang, monde.clubs[ligne.club_id])
                for rang, ligne in enumerate(saison.classement_final, start=1)
            ],
        )
        for saison in saisons
    ]


def _recuperer_competition(competition_id: int, etat_serveur: EtatServeur) -> Competition:
    competition = etat_serveur.monde.competitions.get(competition_id)
    if competition is None:
        raise HTTPException(status_code=404, detail="Compétition introuvable")
    return competition
