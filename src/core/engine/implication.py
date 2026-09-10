"""Config's raw per-poste vectors (positional lists) reshaped into
Poste/Zone/Couloir-keyed tables the engine can index safely. See
docs/attributs.md "Matrice d'implication" — impl[zone][couloir] =
impl_vert[zone] * impl_lat[couloir], kept separable rather than
precomputing the full product (7 numbers per poste per phase, not 12).
"""

from dataclasses import dataclass

from core.config.modeles.implications import ConfigImplications
from core.domain.geometrie import COULOIRS_ORDONNES, ZONES_ORDONNEES, Couloir, Zone
from core.domain.poste import Poste

TableVerticale = dict[Poste, dict[Zone, float]]
TableLaterale = dict[Poste, dict[Couloir, float]]


@dataclass(frozen=True, slots=True)
class TablesImplication:
    vertical_attaque: TableVerticale
    vertical_defense: TableVerticale
    lateral: TableLaterale

    def implication(self, poste: Poste, zone: Zone, couloir: Couloir, phase_attaque: bool) -> float:
        table = self.vertical_attaque if phase_attaque else self.vertical_defense
        return table[poste][zone] * self.lateral[poste][couloir]


def _convertir_verticale(source: dict[str, list[float]]) -> TableVerticale:
    return {Poste(poste): dict(zip(ZONES_ORDONNEES, valeurs, strict=True)) for poste, valeurs in source.items()}


def _convertir_laterale(source: dict[str, list[float]]) -> TableLaterale:
    return {
        Poste(poste): dict(zip(COULOIRS_ORDONNES, valeurs, strict=True)) for poste, valeurs in source.items()
    }


def construire_tables_implication(cfg: ConfigImplications) -> TablesImplication:
    return TablesImplication(
        vertical_attaque=_convertir_verticale(cfg.vertical_attaque),
        vertical_defense=_convertir_verticale(cfg.vertical_defense),
        lateral=_convertir_laterale(cfg.lateral),
    )
