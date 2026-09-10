"""Reads the frozen squad-strength snapshot (benchmarks/effectifs/match.json,
written by benchmarks/generer_effectifs.py) and resolves the named
matchups in config/benchmarks.json -> affrontements_reference against
it — see "Effectifs figés" in docs/benchmarks.md: suites must never
recompute strength from the live Monde, or results stop being
comparable run to run.
"""

import json
import re
from pathlib import Path

from core.engine.equipe import Equipe

_MOTIF_NIVEAU_SYNTHETIQUE = re.compile(r"^__NIVEAU_(\d+(?:\.\d+)?)__$")


def charger_effectifs_reference(chemin: Path) -> dict[str, Equipe]:
    with chemin.open("r", encoding="utf-8") as fichier:
        donnees = json.load(fichier)
    return {
        nom: Equipe(club_id=-1, force_attaque=valeurs["force_attaque"], force_defense=valeurs["force_defense"])
        for nom, valeurs in donnees.items()
    }


def resoudre_equipe(nom: str, effectifs: dict[str, Equipe]) -> Equipe:
    """"__NIVEAU_70__" builds a synthetic equal-strength team on the fly
    (used by the "egaux_dom" reference matchup); anything else is looked
    up in the frozen snapshot.
    """
    synthetique = _MOTIF_NIVEAU_SYNTHETIQUE.match(nom)
    if synthetique is not None:
        niveau = float(synthetique.group(1))
        return Equipe(club_id=-1, force_attaque=niveau, force_defense=niveau)

    if nom not in effectifs:
        raise KeyError(
            f"club de reference introuvable dans l'instantane: {nom!r} — "
            "relancer benchmarks/generer_effectifs.py si config/benchmarks.json a change"
        )
    return effectifs[nom]
