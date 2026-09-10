from dataclasses import dataclass
from enum import Enum


class StatutClub(Enum):
    ACTIF = "actif"
    DORMANT = "dormant"


@dataclass(frozen=True, slots=True)
class PersonnaliteClub:
    """Drawn once when the world is created, stable for its lifetime."""

    appetit_risque: float
    preference_jeunes: float
    agressivite_salariale: float
    patience_negociation: float


@dataclass(slots=True)
class Club:
    id: int
    nom: str
    nom_court: str
    pays: str
    competition_id: int  # -1 if unknown/not simulated — see docs/modele-donnees.md

    statut: StatutClub
    reputation: int
    note_centre_formation: int

    budget_transfert: int
    masse_salariale_max: int
    solde: int

    formation_preferee: str  # a key of config/formations.json -> formations
    personnalite: PersonnaliteClub
