"""Game date value object. Never `datetime`: see CLAUDE.md conventions.

`plus_jours`/`jours_jusqua` delegate to `datetime.date` internally purely
for calendar arithmetic (month lengths, leap years) — never to read the
system clock (no `datetime.now()`/`date.today()` anywhere here), which
would break determinism.
"""

import datetime
from dataclasses import dataclass


@dataclass(frozen=True, slots=True, order=True)
class Date:
    annee: int
    mois: int
    jour: int

    @staticmethod
    def depuis_jj_mm_aaaa(chaine: str) -> "Date":
        """Parse a "31.12.2028"-style date, the format used in data/players.csv."""
        jour, mois, annee = chaine.split(".")
        return Date(int(annee), int(mois), int(jour))

    def age_a(self, reference: "Date") -> int:
        """Age in whole years at `reference`, treating self as a birth date."""
        age = reference.annee - self.annee
        if (reference.mois, reference.jour) < (self.mois, self.jour):
            age -= 1
        return age

    def plus_un_an(self) -> "Date":
        return Date(self.annee + 1, self.mois, self.jour)

    def plus_jours(self, n: int) -> "Date":
        resultat = datetime.date(self.annee, self.mois, self.jour) + datetime.timedelta(days=n)
        return Date(resultat.year, resultat.month, resultat.day)

    def jours_jusqua(self, autre: "Date") -> int:
        depart = datetime.date(self.annee, self.mois, self.jour)
        arrivee = datetime.date(autre.annee, autre.mois, autre.jour)
        return (arrivee - depart).days

    def __str__(self) -> str:
        return f"{self.jour:02d}/{self.mois:02d}/{self.annee:04d}"
