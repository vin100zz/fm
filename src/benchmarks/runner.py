"""CLI entry point: python -m benchmarks.runner --suite <nom>|tout [options]
See docs/benchmarks.md.
"""

import argparse
import csv
import json
import sys
import tempfile
from pathlib import Path
from random import Random

from core.config import charger_config
from core.config.chargeur import FICHIERS_CONFIG
from core.config.modeles.racine import Config

from benchmarks import rapport
from benchmarks.rapport import ResultatCible
from benchmarks.suites import match as suite_match
from benchmarks.suites import performance as suite_performance
from benchmarks.suites import stats_match as suite_stats_match

_RACINE = Path(__file__).resolve().parent.parent.parent
_SUITES = {
    "match": suite_match.executer,
    "performance": suite_performance.executer,
    "stats_match": suite_stats_match.executer,
}


def _analyser_arguments(argv: list[str]) -> argparse.Namespace:
    parseur = argparse.ArgumentParser(description="Harnais de benchmarks — voir docs/benchmarks.md")
    parseur.add_argument("--suite", required=True, choices=[*sorted(_SUITES), "tout"])
    parseur.add_argument("--iterations", type=int, default=None)
    parseur.add_argument("--rapport", type=Path, default=None)
    parseur.add_argument("--config", type=Path, default=_RACINE / "config")
    parseur.add_argument(
        "--balayage",
        default=None,
        help="cle.pointee=debut:fin:pas, ex. moteur.analytique.sensibilite_ecart_force=0.02:0.04:0.005",
    )
    return parseur.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _analyser_arguments(argv if argv is not None else sys.argv[1:])

    if args.balayage is not None:
        if args.suite == "tout":
            print("--balayage exige --suite <nom> (pas 'tout')", file=sys.stderr)
            return 2
        return _executer_balayage(args)

    cfg = charger_config(args.config)
    tous_resultats = _executer_suites(args.suite, cfg, args.iterations)

    for nom_suite, resultats in tous_resultats.items():
        rapport.imprimer_console(nom_suite, resultats)
    if args.rapport is not None:
        rapport.ecrire_json(args.rapport, tous_resultats)

    return 1 if rapport.a_echoue(tous_resultats) else 0


def _executer_suites(nom_suite: str, cfg: Config, iterations: int | None) -> dict[str, list[ResultatCible]]:
    noms = sorted(_SUITES) if nom_suite == "tout" else [nom_suite]
    resultats: dict[str, list[ResultatCible]] = {}
    for nom in noms:
        rng = Random(cfg.benchmarks.execution.graine_defaut)
        resultats[nom] = _SUITES[nom](cfg, rng, iterations)
    return resultats


def _analyser_spec_balayage(spec: str) -> tuple[str, float, float, float]:
    chemin, _, plage = spec.partition("=")
    debut_texte, fin_texte, pas_texte = plage.split(":")
    return chemin, float(debut_texte), float(fin_texte), float(pas_texte)


def _construire_surcharge(chemin_config: str, valeur: float, dossier_surcharge: Path) -> None:
    segments = chemin_config.split(".")
    nom_fichier, _classe = FICHIERS_CONFIG[segments[0]]

    contenu: dict = {}
    curseur = contenu
    for segment in segments[1:-1]:
        curseur = curseur.setdefault(segment, {})
    curseur[segments[-1]] = valeur

    with (dossier_surcharge / nom_fichier).open("w", encoding="utf-8") as fichier:
        json.dump(contenu, fichier)


def _valeurs_balayage(debut: float, fin: float, pas: float) -> list[float]:
    valeurs = []
    valeur = debut
    # arrondi pour eviter la derive en virgule flottante sur des pas comme 0.005
    while round(valeur, 10) <= fin:
        valeurs.append(round(valeur, 10))
        valeur += pas
    return valeurs


def _executer_balayage(args: argparse.Namespace) -> int:
    chemin_config_champ, debut, fin, pas = _analyser_spec_balayage(args.balayage)
    lignes: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory() as dossier_temp:
        dossier_surcharge = Path(dossier_temp)
        for valeur in _valeurs_balayage(debut, fin, pas):
            _construire_surcharge(chemin_config_champ, valeur, dossier_surcharge)
            cfg = charger_config(args.config, surcharge=dossier_surcharge)
            rng = Random(cfg.benchmarks.execution.graine_defaut)
            resultats = _SUITES[args.suite](cfg, rng, args.iterations)

            print(f"--- {chemin_config_champ} = {valeur} ---")
            rapport.imprimer_console(args.suite, resultats)

            for resultat in resultats:
                lignes.append(
                    {
                        "parametre": chemin_config_champ,
                        "valeur_parametre": valeur,
                        "cible": resultat.nom,
                        "mesure": resultat.valeur,
                        "statut": resultat.statut,
                    }
                )

    if args.rapport is not None:
        args.rapport.parent.mkdir(parents=True, exist_ok=True)
        with args.rapport.open("w", encoding="utf-8", newline="") as fichier:
            ecrivain = csv.DictWriter(fichier, fieldnames=["parametre", "valeur_parametre", "cible", "mesure", "statut"])
            ecrivain.writeheader()
            ecrivain.writerows(lignes)
        print(f"balayage ecrit : {args.rapport}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
