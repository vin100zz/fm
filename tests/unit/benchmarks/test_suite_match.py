import json
from pathlib import Path
from random import Random

from core.config import Config
from benchmarks.suites.match import executer


NOMS_REELS = ("Paris SG", "Toulouse FC", "Man City", "Burnley", "R. Madrid", "Barcelone")


def ecrire_instantane(chemin: Path, forces: dict[str, float]) -> None:
    donnees = {nom: {"force_attaque": force, "force_defense": force} for nom, force in forces.items()}
    with chemin.open("w", encoding="utf-8") as fichier:
        json.dump(donnees, fichier)


def test_produit_un_resultat_par_issue_et_par_affrontement_plus_la_distribution(
    cfg: Config, tmp_path: Path
) -> None:
    chemin = tmp_path / "match.json"
    ecrire_instantane(chemin, {nom: 60.0 for nom in NOMS_REELS})

    resultats = executer(cfg, Random(1), iterations=200, chemin_effectifs=chemin)

    nb_affrontements = len(cfg.benchmarks.affrontements_reference)
    assert len(resultats) == nb_affrontements * 3 + 4  # victoire/nul/defaite + 4 lignes de distribution
    assert all(resultat.statut in ("ok", "echec") for resultat in resultats)


def test_les_trois_issues_couvrent_tous_les_matches(cfg: Config, tmp_path: Path) -> None:
    chemin = tmp_path / "match.json"
    ecrire_instantane(chemin, {nom: 60.0 for nom in NOMS_REELS})
    n = 300

    resultats = executer(cfg, Random(2), iterations=n, chemin_effectifs=chemin)

    premier_id = cfg.benchmarks.affrontements_reference[0].id
    parts = [r.valeur for r in resultats if r.nom.startswith(f"{premier_id}/")]
    assert sum(parts) == 1.0  # victoire+nul+defaite epuisent les n matches


def test_deterministe_avec_la_meme_graine(cfg: Config, tmp_path: Path) -> None:
    chemin = tmp_path / "match.json"
    ecrire_instantane(chemin, {nom: 60.0 for nom in NOMS_REELS})

    a = executer(cfg, Random(42), iterations=100, chemin_effectifs=chemin)
    b = executer(cfg, Random(42), iterations=100, chemin_effectifs=chemin)

    assert [r.valeur for r in a] == [r.valeur for r in b]


def test_equipe_nettement_plus_forte_gagne_largement_plus_souvent(cfg: Config, tmp_path: Path) -> None:
    chemin = tmp_path / "match.json"
    forces = {nom: 60.0 for nom in NOMS_REELS}
    forces["Paris SG"] = 95.0  # tres au-dessus de Toulouse FC
    ecrire_instantane(chemin, forces)

    resultats = executer(cfg, Random(3), iterations=500, chemin_effectifs=chemin)

    victoire_psg = next(r for r in resultats if r.nom == "psg_dom_toulouse/victoire")
    assert victoire_psg.valeur > 0.6
