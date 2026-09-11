"""Domain-object factories shared across core/world unit tests — see
"fabriques de test" in docs/architecture.md.
"""

from core.domain.attributs import Attributs
from core.domain.club import Club, PersonnaliteClub, StatutClub
from core.domain.contrat import Contrat
from core.domain.date import Date
from core.domain.joueur import Joueur
from core.domain.poste import Poste

DATE = Date(2026, 8, 10)


def des_attributs(**overrides: int) -> Attributs:
    valeurs = {
        "passe": 50, "technique": 50, "finition": 50, "tacle": 50, "jeu_tete": 50,
        "vision": 50, "placement": 50, "sang_froid": 50, "vitesse": 50, "endurance": 50,
        "reflexes": 50, "sorties": 50, "relance": 50,
    }
    valeurs.update(overrides)
    return Attributs(**valeurs)


def un_club(**overrides) -> Club:
    valeurs = dict(
        id=1, nom="Club Test", nom_court="Club Test", pays="ENG", competition_id=11,
        statut=StatutClub.ACTIF, reputation=60, note_centre_formation=40,
        budget_transfert=1_000_000, masse_salariale_max=500_000, solde=0,
        formation_preferee="4-4-2",
        personnalite=PersonnaliteClub(0.5, 0.5, 0.5, 0.5),
    )
    valeurs.update(overrides)
    return Club(**valeurs)


def un_joueur(**overrides) -> Joueur:
    valeurs = dict(
        id=100, nom="Nom", prenom="Prenom", nationalite="FRA", date_naissance=Date(2000, 1, 1),
        poste=Poste.MC, attributs=des_attributs(), potentiel=60,
        forme=1.0, fatigue=1.0, moral=0.6, fragilite=1.0,
        club_id=1, contrat=Contrat(salaire_hebdo=10_000, date_fin=Date(2028, 6, 30), date_signature=DATE),
    )
    valeurs.update(overrides)
    return Joueur(**valeurs)


def un_effectif_complet(club_id: int) -> list[Joueur]:
    joueurs = [un_joueur(id=200 + i, poste=Poste.MC, club_id=club_id) for i in range(15)]
    joueurs.append(un_joueur(id=999, poste=Poste.GB, club_id=club_id))
    return joueurs
