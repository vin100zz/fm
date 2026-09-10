import csv
import json
from pathlib import Path

from benchmarks.runner import _analyser_spec_balayage, _construire_surcharge, _valeurs_balayage, main


class TestValeursBalayage:
    def test_couvre_debut_et_fin_inclus(self) -> None:
        assert _valeurs_balayage(0.02, 0.04, 0.01) == [0.02, 0.03, 0.04]

    def test_pas_qui_ne_tombe_pas_pile_sur_la_fin(self) -> None:
        assert _valeurs_balayage(0.0, 0.05, 0.02) == [0.0, 0.02, 0.04]

    def test_resiste_a_la_derive_en_virgule_flottante(self) -> None:
        valeurs = _valeurs_balayage(0.1, 0.3, 0.05)
        assert valeurs == [0.1, 0.15, 0.2, 0.25, 0.3]


def test_analyser_spec_balayage() -> None:
    chemin, debut, fin, pas = _analyser_spec_balayage(
        "moteur.analytique.sensibilite_ecart_force=0.02:0.04:0.005"
    )
    assert chemin == "moteur.analytique.sensibilite_ecart_force"
    assert (debut, fin, pas) == (0.02, 0.04, 0.005)


def test_construire_surcharge_ecrit_la_cle_imbriquee(tmp_path: Path) -> None:
    _construire_surcharge("moteur.analytique.sensibilite_ecart_force", 0.033, tmp_path)

    with (tmp_path / "moteur_match.json").open(encoding="utf-8") as fichier:
        contenu = json.load(fichier)
    assert contenu == {"analytique": {"sensibilite_ecart_force": 0.033}}


class TestMain:
    def test_suite_performance_reussit(self, dossier_config: Path) -> None:
        code = main(["--suite", "performance", "--config", str(dossier_config)])
        assert code == 0

    def test_ecrit_un_rapport_json(self, dossier_config: Path, tmp_path: Path) -> None:
        chemin_rapport = tmp_path / "rapport.json"
        main(["--suite", "performance", "--config", str(dossier_config), "--rapport", str(chemin_rapport)])

        with chemin_rapport.open(encoding="utf-8") as fichier:
            donnees = json.load(fichier)
        assert "performance" in donnees

    def test_balayage_ecrit_une_ligne_par_cible_et_par_valeur(
        self, dossier_config: Path, tmp_path: Path
    ) -> None:
        chemin_rapport = tmp_path / "balayage.csv"
        code = main(
            [
                "--suite", "match",
                "--iterations", "20",
                "--config", str(dossier_config),
                "--balayage", "moteur.analytique.sensibilite_ecart_force=0.02:0.03:0.01",
                "--rapport", str(chemin_rapport),
            ]
        )

        assert code == 0
        with chemin_rapport.open(encoding="utf-8", newline="") as fichier:
            lignes = list(csv.DictReader(fichier))
        valeurs_testees = {ligne["valeur_parametre"] for ligne in lignes}
        assert valeurs_testees == {"0.02", "0.03"}

    def test_balayage_refuse_suite_tout(self, dossier_config: Path) -> None:
        code = main(
            [
                "--suite", "tout",
                "--config", str(dossier_config),
                "--balayage", "moteur.analytique.sensibilite_ecart_force=0.02:0.03:0.01",
            ]
        )
        assert code == 2
