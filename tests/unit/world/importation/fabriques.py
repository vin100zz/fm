"""Row factories matching the real column names of data/clubs.csv and
data/players.csv (see docs/modele-donnees.md) — override only what a
given test cares about, per "fabriques de test" in docs/architecture.md.
"""


def une_ligne_club(**overrides: str) -> dict[str, str]:
    ligne = {
        "Unique ID": "1000",
        "Name": "Club Test",
        "Nation": "Angleterre",
        "Division": "Premier League",
        "Status": "Professional",
        "Stad Cap": "40000",
        "Division ID": "11",
    }
    ligne.update(overrides)
    return ligne


def une_ligne_joueur(**overrides: str) -> dict[str, str]:
    ligne = {
        "Name": "Nom, Prenom",
        "Nation": "France",
        "Position": "M C",
        "Club": "Club Test",
        "Int Caps": "0",
        "Int Goals": "0",
        "Wage": "10000",
        "Value": "5000000",
        "Date Of Birth": "01.01.2000",
        "Contract End": "30.06.2028",
        "Unique ID": "2000",
        "Club ID": "1000",
    }
    ligne.update(overrides)
    return ligne
