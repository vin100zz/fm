"""GET /api/matches/{id} — "Match" screen in docs/ui.md: full report.

`Match`/`ResultatMatch` don't retain the starting XI as a separate
field — `resultat.notes` (one rating per player who started) already
has exactly that set, split by `Joueur.club_id` here rather than
duplicating it on `Match`. Live substitutions aren't wired into the
season loop yet (see `core/world/saison.py`), so this always matches
who actually played.
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.etat_serveur import EtatServeur, obtenir_etat
from core.domain.joueur import Joueur
from core.domain.match import Evenement, StatsEquipe

routeur = APIRouter()


class VueEvenementMatch(BaseModel):
    minute: int
    type: str
    joueur_id: int
    joueur_nom: str
    joueur_secondaire_id: int | None
    joueur_secondaire_nom: str | None
    detail: str | None


class VueJoueurNote(BaseModel):
    joueur_id: int
    nom: str
    prenom: str
    poste: str
    note: float


class VueStatsEquipe(BaseModel):
    tirs: int | None
    xg: float | None
    possession_pct: float | None
    corners: int | None
    cartons_jaunes: int | None
    cartons_rouges: int | None


class VueMatchDetail(BaseModel):
    id: int
    competition_id: int
    competition_nom: str
    journee: int
    date: str
    domicile_id: int
    domicile_nom: str
    exterieur_id: int
    exterieur_nom: str
    buts_dom: int
    buts_ext: int
    stats_dom: VueStatsEquipe
    stats_ext: VueStatsEquipe
    evenements: list[VueEvenementMatch]
    composition_dom: list[VueJoueurNote]
    composition_ext: list[VueJoueurNote]


@routeur.get("/{match_id}", response_model=VueMatchDetail)
def detail_match(match_id: int, etat_serveur: EtatServeur = Depends(obtenir_etat)) -> VueMatchDetail:
    monde = etat_serveur.monde
    match = monde.matches.get(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match introuvable")
    if match.resultat is None:
        raise HTTPException(status_code=409, detail="Ce match n'a pas encore été joué")

    resultat = match.resultat
    competition = monde.competitions.get(match.competition_id)

    return VueMatchDetail(
        id=match.id, competition_id=match.competition_id, competition_nom=competition.nom if competition else "",
        journee=match.journee, date=str(match.date),
        domicile_id=match.domicile_id, domicile_nom=monde.clubs[match.domicile_id].nom,
        exterieur_id=match.exterieur_id, exterieur_nom=monde.clubs[match.exterieur_id].nom,
        buts_dom=resultat.buts_dom, buts_ext=resultat.buts_ext,
        stats_dom=_vue_stats(resultat.stats_dom), stats_ext=_vue_stats(resultat.stats_ext),
        evenements=[_vue_evenement(e, monde) for e in resultat.evenements],
        composition_dom=_vue_composition(match.domicile_id, resultat.notes, monde),
        composition_ext=_vue_composition(match.exterieur_id, resultat.notes, monde),
    )


def _vue_stats(stats: StatsEquipe) -> VueStatsEquipe:
    return VueStatsEquipe(**asdict(stats))


def _nom_joueur(joueur_id: int | None, monde) -> str | None:
    if joueur_id is None:
        return None
    joueur = monde.joueurs.get(joueur_id)
    return f"{joueur.prenom} {joueur.nom}".strip() if joueur else None


def _vue_evenement(evenement: Evenement, monde) -> VueEvenementMatch:
    return VueEvenementMatch(
        minute=evenement.minute, type=evenement.type.value, joueur_id=evenement.joueur_id,
        joueur_nom=_nom_joueur(evenement.joueur_id, monde) or "?",
        joueur_secondaire_id=evenement.joueur_secondaire_id,
        joueur_secondaire_nom=_nom_joueur(evenement.joueur_secondaire_id, monde), detail=evenement.detail,
    )


def _vue_composition(club_id: int, notes: dict[int, float], monde) -> list[VueJoueurNote]:
    composition = []
    for joueur_id, note in notes.items():
        joueur: Joueur | None = monde.joueurs.get(joueur_id)
        if joueur is None or joueur.club_id != club_id:
            continue
        composition.append(VueJoueurNote(joueur_id=joueur.id, nom=joueur.nom, prenom=joueur.prenom, poste=joueur.poste.value, note=round(note, 1)))
    return composition
