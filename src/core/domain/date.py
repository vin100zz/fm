"""Game date value object. Never `datetime`: see CLAUDE.md conventions."""

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

    def __str__(self) -> str:
        return f"{self.jour:02d}/{self.mois:02d}/{self.annee:04d}"
