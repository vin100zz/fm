"""Long-lived records that outlive a season. See "Historique et
volumétrie" in docs/modele-donnees.md.

`transferts` actually populated from `core/world/mercato.py` (the
import pipeline only ever seeded it empty); `palmares` from the
end-of-season rollover (`core/world/saison.py`) — both added exactly as
this module's docstring long anticipated: a local, additive change, not
a redesign. `trajectoires_attributs` still isn't produced by anything.
`SaisonTerminee` only records the champion and final table, not a
season's top scorer/passer — nothing aggregates per-player match
events across a season yet (see docs/ui.md).

`LigneHistoriqueJoueur` (2026-09-11, ajouté) isn't itself a field of
`Historique` — nothing persists it. It's the return shape of
`core/world/historique_joueur.py::historique_saisons`, computed on
demand from `Historique.transferts` plus `Monde.matches` for the
"Historique" section of la fiche joueur (docs/ui.md).
"""

from dataclasses import dataclass, field

from core.domain.classement import LigneClassement
from core.domain.date import Date


@dataclass(frozen=True, slots=True)
class TransfertHistorique:
    date: Date
    joueur_id: int
    club_source_id: int | None
    club_cible_id: int | None
    montant: int
    # Monde.saison au moment du transfert — filtrage cote API
    # (GET /api/clubs/{id}/transferts?saison=), comme Match.saison.
    saison: int = 1


@dataclass(frozen=True, slots=True)
class SaisonTerminee:
    competition_id: int
    saison: int
    classement_final: list[LigneClassement]

    @property
    def champion_id(self) -> int:
        return self.classement_final[0].club_id


@dataclass(slots=True)
class Historique:
    transferts: list[TransfertHistorique] = field(default_factory=list)
    palmares: list[SaisonTerminee] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class LigneHistoriqueJoueur:
    saison: int
    club_id: int | None
    matches_joues: int
    buts: int
    note_moyenne: float
    prix_transfert: int | None = None  # le transfert qui a amene le joueur a ce club cette saison-la, s'il y en a un
