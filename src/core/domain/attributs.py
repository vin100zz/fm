"""The 13 player attributes. See docs/attributs.md — a fixed set of named
fields on purpose: composite formulas access them by name
(`cfg.composites.tir.finition`), a generic dict would defeat typing.
"""

import dataclasses
from dataclasses import dataclass


@dataclass(slots=True)
class Attributs:
    # Techniques
    passe: int
    technique: int
    finition: int
    tacle: int
    jeu_tete: int
    # Mentaux
    vision: int
    placement: int
    sang_froid: int
    # Physiques
    vitesse: int
    endurance: int
    # Gardien
    reflexes: int
    sorties: int
    relance: int

    def valeur(self, nom: str) -> int:
        """Read an attribute by its config-file name, for composite formulas
        such as `sum(poids * attributs.valeur(nom) for nom, poids in composite.items())`.
        """
        return getattr(self, nom)


NOMS_ATTRIBUTS: tuple[str, ...] = tuple(champ.name for champ in dataclasses.fields(Attributs))


def combinaison_ponderee(attributs: Attributs, poids: dict[str, float]) -> float:
    """Any composite (note_globale, progression_attaque, tir...) is this
    same operation against a different weight table from config/attributs.json.
    """
    return sum(coefficient * attributs.valeur(nom) for nom, coefficient in poids.items())
