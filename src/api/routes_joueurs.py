"""GET /api/joueurs/* — "Recherche de joueurs" and "Joueur" screens in
docs/ui.md. `lister` searches the full ~32 000-player population
(active and dormant), always paginated.

"Saison en cours" (matches, minutes, buts, passes, cartons) and
"Historique" aren't in `VueJoueurDetail`: nothing aggregates a
player's events across matches yet, and there's no season-boundary to
close a season's stats against.
"""

from fastapi import APIRouter, Depends, HTTPException

from api.etat_serveur import EtatServeur, obtenir_etat
from api.pagination import Page, paginer
from api.vues import VueJoueurDetail, VueJoueurLigne, vue_joueur_detail, vue_joueur_ligne
from core.domain.joueur import Joueur
from core.domain.poste import Poste
from core.world.note_globale import note_globale

routeur = APIRouter()


@routeur.get("", response_model=Page[VueJoueurLigne])
def lister_joueurs(
    poste: str | None = None,
    age_min: int | None = None,
    age_max: int | None = None,
    niveau_min: float | None = None,
    nation: str | None = None,
    club: int | None = None,
    statut_club: str | None = None,
    tri: str = "niveau",
    page: int = 1,
    etat_serveur: EtatServeur = Depends(obtenir_etat),
) -> Page[VueJoueurLigne]:
    monde = etat_serveur.monde
    cfg = etat_serveur.cfg
    joueurs = list(monde.joueurs.values())

    if poste is not None:
        try:
            poste_filtre = Poste(poste)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"poste inconnu: {poste}")
        joueurs = [j for j in joueurs if j.poste is poste_filtre]
    if age_min is not None:
        joueurs = [j for j in joueurs if j.date_naissance.age_a(monde.date) >= age_min]
    if age_max is not None:
        joueurs = [j for j in joueurs if j.date_naissance.age_a(monde.date) <= age_max]
    if nation is not None:
        joueurs = [j for j in joueurs if j.nationalite == nation]
    if club is not None:
        joueurs = [j for j in joueurs if j.club_id == club]
    if statut_club is not None:
        joueurs = [j for j in joueurs if j.club_id is not None and monde.clubs[j.club_id].statut.value == statut_club]
    if niveau_min is not None:
        joueurs = [j for j in joueurs if note_globale(j, cfg.attributs) >= niveau_min]

    if tri == "age":
        joueurs.sort(key=lambda j: j.date_naissance.age_a(monde.date))
    elif tri == "nom":
        joueurs.sort(key=lambda j: j.nom)
    else:
        joueurs.sort(key=lambda j: note_globale(j, cfg.attributs), reverse=True)

    vues = [vue_joueur_ligne(j, monde.date, cfg, monde.clubs.get(j.club_id)) for j in joueurs]
    return paginer(vues, page)


@routeur.get("/{joueur_id}", response_model=VueJoueurDetail)
def detail_joueur(joueur_id: int, etat_serveur: EtatServeur = Depends(obtenir_etat)) -> VueJoueurDetail:
    joueur = _recuperer_joueur(joueur_id, etat_serveur)
    club = etat_serveur.monde.clubs.get(joueur.club_id)
    return vue_joueur_detail(joueur, etat_serveur.monde.date, etat_serveur.cfg, club)


def _recuperer_joueur(joueur_id: int, etat_serveur: EtatServeur) -> Joueur:
    joueur = etat_serveur.monde.joueurs.get(joueur_id)
    if joueur is None:
        raise HTTPException(status_code=404, detail="Joueur introuvable")
    return joueur
