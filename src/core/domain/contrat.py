from dataclasses import dataclass

from core.domain.date import Date


@dataclass(frozen=True, slots=True)
class Contrat:
    salaire_hebdo: int
    date_fin: Date
    date_signature: Date
