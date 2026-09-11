"""POST/GET /api/partie/* — save/load a game, CLAUDE.md: "sauvegarde de
partie en JSON gzippé, pas de base". Saves live under `saves/` at the
project root (gitignored — user data, not source, like `data/` isn't
version-controlled game content either).
"""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.etat_serveur import EtatServeur, obtenir_etat
from core.world.persistance import charger, lister_sauvegardes, sauvegarder

routeur = APIRouter()
DOSSIER_SAUVEGARDES = Path(__file__).resolve().parent.parent.parent / "saves"


class RequeteSlot(BaseModel):
    slot: str


class VueSlot(BaseModel):
    slot: str
    taille_octets: int
    modifie_le: str


def _chemin_slot(slot: str) -> Path:
    nom = "".join(c for c in slot if c.isalnum() or c in "-_") or "partie"
    return DOSSIER_SAUVEGARDES / f"{nom}.json.gz"


@routeur.post("/sauvegarder")
def sauvegarder_partie(requete: RequeteSlot, etat_serveur: EtatServeur = Depends(obtenir_etat)) -> dict:
    sauvegarder(etat_serveur.monde, etat_serveur.rng, _chemin_slot(requete.slot))
    return {"ok": True}


@routeur.post("/charger")
def charger_partie(requete: RequeteSlot, etat_serveur: EtatServeur = Depends(obtenir_etat)) -> dict:
    chemin = _chemin_slot(requete.slot)
    if not chemin.exists():
        raise HTTPException(status_code=404, detail="Sauvegarde introuvable")

    monde, rng = charger(chemin)
    etat_serveur.monde = monde
    etat_serveur.rng = rng
    etat_serveur.dernier_journal = []
    return {"ok": True}


@routeur.get("/slots", response_model=list[VueSlot])
def lister_slots() -> list[VueSlot]:
    return [
        VueSlot(slot=info.slot, taille_octets=info.taille_octets, modifie_le=datetime.fromtimestamp(info.modifie_le).strftime("%d/%m/%Y %H:%M"))
        for info in lister_sauvegardes(DOSSIER_SAUVEGARDES)
    ]
