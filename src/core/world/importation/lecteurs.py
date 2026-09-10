"""CSV -> raw dict rows. No parsing, no typing, no domain knowledge here —
see docs/modele-donnees.md for the real column names of
data/clubs.csv and data/players.csv (semicolon-delimited, cp1252).
A future change of source format only touches this file.
"""

import csv
from pathlib import Path

_ENCODAGE = "cp1252"
_DIALECTE = {"delimiter": ";", "quotechar": '"'}


def _lire_csv(chemin: Path) -> list[dict[str, str]]:
    with chemin.open("r", encoding=_ENCODAGE, newline="") as fichier:
        return list(csv.DictReader(fichier, **_DIALECTE))


def lire_clubs(chemin: Path) -> list[dict[str, str]]:
    return _lire_csv(chemin)


def lire_joueurs(chemin: Path) -> list[dict[str, str]]:
    return _lire_csv(chemin)
