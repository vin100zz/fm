"""Result shape and console/JSON output for every suite. See
docs/benchmarks.md — "une ligne par cible, verte ou rouge, avec valeur
mesurée, cible, tolérance et écart", plus JSON for historisation.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from core.config.modeles.commun import Plage

Statut = Literal["ok", "echec", "non_mesurable"]

_LIBELLE_STATUT = {"ok": "OK", "echec": "ECHEC", "non_mesurable": "N/A"}


@dataclass(frozen=True, slots=True)
class ResultatCible:
    nom: str
    valeur: float | None
    description_cible: str
    statut: Statut

    @staticmethod
    def depuis_tolerance(nom: str, mesure: float, cible: float, tolerance: float) -> "ResultatCible":
        ok = abs(mesure - cible) <= tolerance
        return ResultatCible(
            nom=nom,
            valeur=mesure,
            description_cible=f"cible {cible} +/-{tolerance}",
            statut="ok" if ok else "echec",
        )

    @staticmethod
    def depuis_plage(nom: str, mesure: float, plage: Plage) -> "ResultatCible":
        ok = plage.min <= mesure <= plage.max
        return ResultatCible(
            nom=nom,
            valeur=mesure,
            description_cible=f"cible [{plage.min}, {plage.max}]",
            statut="ok" if ok else "echec",
        )


def imprimer_console(nom_suite: str, resultats: list[ResultatCible]) -> None:
    for resultat in resultats:
        valeur_texte = f"{resultat.valeur:.3f}" if resultat.valeur is not None else "-"
        print(
            f"{nom_suite}/{resultat.nom:<45} {valeur_texte:>10}   "
            f"{resultat.description_cible:<30} {_LIBELLE_STATUT[resultat.statut]}"
        )


def ecrire_json(chemin: Path, tous_resultats: dict[str, list[ResultatCible]]) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    donnees = {
        nom_suite: [asdict(resultat) for resultat in resultats]
        for nom_suite, resultats in tous_resultats.items()
    }
    with chemin.open("w", encoding="utf-8") as fichier:
        json.dump(donnees, fichier, ensure_ascii=False, indent=2)


def a_echoue(tous_resultats: dict[str, list[ResultatCible]]) -> bool:
    return any(
        resultat.statut == "echec" for resultats in tous_resultats.values() for resultat in resultats
    )
