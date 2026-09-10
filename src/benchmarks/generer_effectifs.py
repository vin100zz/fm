"""One-off generator for benchmarks/effectifs/match.json: computes and
freezes the squad strength (core.engine.equipe.Equipe) of every club
named in config/benchmarks.json -> affrontements_reference, from a
fresh import of data/.

Run by hand when you deliberately want a new snapshot — see "Effectifs
figés" in docs/benchmarks.md. Never call this from a suite: benchmark
results must stay comparable run to run, which means not silently
recomputing strength from whatever data/ or the synthesis config
currently look like.

    python -m benchmarks.generer_effectifs
"""

import json
import re
from pathlib import Path
from random import Random

from core.config import charger_config
from core.domain.club import StatutClub
from core.domain.date import Date
from core.engine.equipe import equipe_depuis_effectif
from core.world.importation import importer_monde

_RACINE = Path(__file__).resolve().parent.parent.parent
_MOTIF_NIVEAU_SYNTHETIQUE = re.compile(r"^__NIVEAU_(\d+(?:\.\d+)?)__$")
_CHEMIN_INSTANTANE = Path(__file__).resolve().parent / "effectifs" / "match.json"

# The import pipeline needs a "game start" date to age players and judge
# contracts (core never reads the clock itself — see CLAUDE.md); a fixed
# date keeps this generator's output reproducible.
_DATE_DEBUT = Date(2026, 8, 10)


def main() -> None:
    cfg = charger_config(_RACINE / "config")
    graine = cfg.benchmarks.execution.graine_defaut
    monde, _avertissements = importer_monde(_RACINE / "data", cfg, _DATE_DEBUT, graine, Random(graine))

    noms = {
        nom
        for affrontement in cfg.benchmarks.affrontements_reference
        for nom in (affrontement.domicile, affrontement.exterieur)
        if not _MOTIF_NIVEAU_SYNTHETIQUE.match(nom)
    }

    instantane: dict[str, dict[str, float]] = {}
    for nom in sorted(noms):
        club = next(
            (c for c in monde.clubs.values() if c.nom == nom and c.statut is StatutClub.ACTIF), None
        )
        if club is None:
            raise SystemExit(
                f"club de reference introuvable ou non actif dans data/clubs.csv: {nom!r} "
                "(voir la _note de config/benchmarks.json pour la correspondance des noms)"
            )
        equipe = equipe_depuis_effectif(club.id, monde.joueurs, cfg)
        instantane[nom] = {"force_attaque": equipe.force_attaque, "force_defense": equipe.force_defense}

    _CHEMIN_INSTANTANE.parent.mkdir(exist_ok=True)
    with _CHEMIN_INSTANTANE.open("w", encoding="utf-8") as fichier:
        json.dump(instantane, fichier, ensure_ascii=False, indent=2, sort_keys=True)

    print(f"instantane ecrit : {_CHEMIN_INSTANTANE}")
    for nom, valeurs in sorted(instantane.items()):
        print(f"  {nom}: attaque={valeurs['force_attaque']:.1f} defense={valeurs['force_defense']:.1f}")


if __name__ == "__main__":
    main()
