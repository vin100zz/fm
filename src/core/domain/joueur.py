from dataclasses import dataclass, field

from core.domain.attributs import Attributs
from core.domain.contrat import Contrat
from core.domain.date import Date
from core.domain.etat_joueur import Blessure, Suspension
from core.domain.poste import Poste


@dataclass(slots=True)
class Joueur:
    id: int
    nom: str
    prenom: str
    nationalite: str
    date_naissance: Date

    poste: Poste
    attributs: Attributs
    potentiel: int  # true value, never exposed as-is — see docs/progression-demographie.md

    # No hardcoded defaults here: initial forme/fatigue/moral come from
    # config/etats.json, passed explicitly by whoever constructs a Joueur.
    forme: float
    fatigue: float
    moral: float

    postes_secondaires: dict[Poste, float] = field(default_factory=dict)
    blessure: Blessure | None = None
    suspension: Suspension | None = None
    club_id: int | None = None
    contrat: Contrat | None = None
