import json
from pathlib import Path

from core.config.modeles.commun import Plage
from benchmarks.rapport import ResultatCible, a_echoue, ecrire_json, imprimer_console


class TestDepuisTolerance:
    def test_dans_la_tolerance_est_ok(self) -> None:
        resultat = ResultatCible.depuis_tolerance("x", mesure=0.72, cible=0.75, tolerance=0.05)
        assert resultat.statut == "ok"

    def test_hors_tolerance_est_echec(self) -> None:
        resultat = ResultatCible.depuis_tolerance("x", mesure=0.60, cible=0.75, tolerance=0.05)
        assert resultat.statut == "echec"

    def test_tout_juste_dans_la_borne_est_ok(self) -> None:
        resultat = ResultatCible.depuis_tolerance("x", mesure=0.701, cible=0.75, tolerance=0.05)
        assert resultat.statut == "ok"


class TestDepuisPlage:
    def test_dans_la_plage_est_ok(self) -> None:
        resultat = ResultatCible.depuis_plage("x", mesure=1.4, plage=Plage(min=1.3, max=1.6))
        assert resultat.statut == "ok"

    def test_hors_plage_est_echec(self) -> None:
        resultat = ResultatCible.depuis_plage("x", mesure=2.0, plage=Plage(min=1.3, max=1.6))
        assert resultat.statut == "echec"


def test_a_echoue_detecte_le_moindre_echec() -> None:
    resultats = {
        "match": [ResultatCible("a", 1.0, "-", "ok")],
        "performance": [ResultatCible("b", None, "-", "non_mesurable"), ResultatCible("c", 1.0, "-", "echec")],
    }
    assert a_echoue(resultats)


def test_a_echoue_faux_si_tout_est_ok_ou_non_mesurable() -> None:
    resultats = {
        "match": [ResultatCible("a", 1.0, "-", "ok")],
        "performance": [ResultatCible("b", None, "-", "non_mesurable")],
    }
    assert not a_echoue(resultats)


def test_imprimer_console_ne_plante_pas_avec_valeur_none(capsys) -> None:
    imprimer_console("performance", [ResultatCible("x", None, "n/a", "non_mesurable")])
    assert "x" in capsys.readouterr().out


def test_ecrire_json_fait_un_aller_retour(tmp_path: Path) -> None:
    resultats = {"match": [ResultatCible("psg/victoire", 0.66, "cible 0.75 +/-0.05", "echec")]}
    chemin = tmp_path / "sous_dossier" / "rapport.json"

    ecrire_json(chemin, resultats)

    with chemin.open(encoding="utf-8") as fichier:
        relu = json.load(fichier)
    assert relu["match"][0]["nom"] == "psg/victoire"
    assert relu["match"][0]["statut"] == "echec"
