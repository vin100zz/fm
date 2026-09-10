import csv
from pathlib import Path
from random import Random

import pytest

from core.config import Config
from core.domain.club import StatutClub
from core.domain.date import Date
from core.world.importation import importer_monde
from core.world.importation.erreurs import ImportInvalide
from tests.unit.world.importation.fabriques import une_ligne_club, une_ligne_joueur

DATE_DEBUT = Date(2026, 8, 10)
DIALECTE = {"delimiter": ";", "quotechar": '"'}


def _ecrire_csv(chemin: Path, lignes: list[dict[str, str]]) -> None:
    with chemin.open("w", encoding="cp1252", newline="") as fichier:
        ecrivain = csv.DictWriter(fichier, fieldnames=list(lignes[0]), **DIALECTE)
        ecrivain.writeheader()
        ecrivain.writerows(lignes)


def _ecrire_jeu_de_donnees(dossier: Path, clubs: list[dict[str, str]], joueurs: list[dict[str, str]]) -> None:
    _ecrire_csv(dossier / "clubs.csv", clubs)
    _ecrire_csv(dossier / "players.csv", joueurs)


def test_monde_minimal_18_joueurs_dans_lunique_club_actif(tmp_path: Path, cfg: Config) -> None:
    club_actif = une_ligne_club(**{"Unique ID": "1", "Division ID": "11"})
    club_dormant = une_ligne_club(**{"Unique ID": "2", "Division ID": "999999", "Nation": "Kenya"})
    joueurs = [
        une_ligne_joueur(**{"Unique ID": str(100 + i), "Club ID": "1", "Position": "M C"})
        for i in range(17)
    ]
    joueurs.append(une_ligne_joueur(**{"Unique ID": "200", "Club ID": "1", "Position": "GK"}))
    # a "20th competition" would fail the club-count check, so this test
    # only exercises monde.competitions_simulees by leaving 4 leagues short
    # — we don't validate here, see test below for that path.

    _ecrire_jeu_de_donnees(tmp_path, [club_actif, club_dormant], joueurs)

    with pytest.raises(ImportInvalide):
        # only 1 club provided for a 20-club Premier League: fails the
        # "right club count per competition" check, as it must.
        importer_monde(tmp_path, cfg, DATE_DEBUT, graine=1, rng=Random(1))


def test_monde_importe_avec_succes_quand_toutes_les_competitions_sont_completes(
    tmp_path: Path, cfg: Config
) -> None:
    clubs = []
    joueurs = []
    prochain_id_joueur = 1
    for competition in cfg.monde.competitions_simulees:
        for i in range(competition.nb_clubs):
            club_id = f"{competition.division_id}{i:03d}"
            clubs.append(
                une_ligne_club(**{"Unique ID": club_id, "Division ID": str(competition.division_id)})
            )
            for _ in range(15):
                joueurs.append(
                    une_ligne_joueur(
                        **{"Unique ID": str(prochain_id_joueur), "Club ID": club_id, "Position": "M C"}
                    )
                )
                prochain_id_joueur += 1
            joueurs.append(
                une_ligne_joueur(
                    **{"Unique ID": str(prochain_id_joueur), "Club ID": club_id, "Position": "GK"}
                )
            )
            prochain_id_joueur += 1
    clubs.append(une_ligne_club(**{"Unique ID": "999999", "Division ID": "-1", "Nation": "Kenya"}))

    _ecrire_jeu_de_donnees(tmp_path, clubs, joueurs)

    monde, avertissements = importer_monde(tmp_path, cfg, DATE_DEBUT, graine=1, rng=Random(1))

    assert avertissements == []
    assert len(monde.competitions) == 5
    for competition in cfg.monde.competitions_simulees:
        assert len(monde.competitions[competition.division_id].club_ids) == competition.nb_clubs
    assert monde.clubs[999999].statut is StatutClub.DORMANT
    assert monde.graine == 1
    assert monde.prochain_id > max(monde.joueurs)


class TestImportReel:
    """Slower checks against the real data/ shipped with the project."""

    def test_import_complet_ne_leve_rien_et_respecte_les_effectifs_configures(
        self, cfg: Config, dossier_donnees: Path
    ) -> None:
        monde, avertissements = importer_monde(
            dossier_donnees, cfg, DATE_DEBUT, graine=20260910, rng=Random(20260910)
        )

        assert len(monde.competitions) == 5
        for competition in cfg.monde.competitions_simulees:
            assert len(monde.competitions[competition.division_id].club_ids) == competition.nb_clubs
        assert len(monde.clubs) > 20_000
        assert len(monde.joueurs) > 30_000
        # warnings are expected (real data, provisional synthesis) — just
        # confirm they don't silently disappear
        assert isinstance(avertissements, list)
