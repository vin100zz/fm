"""JSON -> validated, typed Config. Fails fast: see docs/configuration.md."""

import json
from pathlib import Path

from pydantic import ValidationError

from core.config.coherence import verifier_coherence
from core.config.erreurs import ConfigInvalide
from core.config.fusion import fusionner, retirer_notes
from core.config.modeles.attributs import ConfigAttributs
from core.config.modeles.benchmarks import ConfigBenchmarks
from core.config.modeles.demographie import ConfigDemographie
from core.config.modeles.etats import ConfigEtats
from core.config.modeles.formations import ConfigFormations
from core.config.modeles.ia_gestion import ConfigIA
from core.config.modeles.implications import ConfigImplications
from core.config.modeles.import_donnees import ConfigImport
from core.config.modeles.moteur_match import ConfigMoteur
from core.config.modeles.monde import ConfigMonde
from core.config.modeles.racine import Config

_FICHIERS: dict[str, tuple[str, type]] = {
    "monde": ("monde.json", ConfigMonde),
    "attributs": ("attributs.json", ConfigAttributs),
    "implications": ("implications.json", ConfigImplications),
    "formations": ("formations.json", ConfigFormations),
    "moteur": ("moteur_match.json", ConfigMoteur),
    "etats": ("etats.json", ConfigEtats),
    "ia": ("ia_gestion.json", ConfigIA),
    "demographie": ("demographie.json", ConfigDemographie),
    "benchmarks": ("benchmarks.json", ConfigBenchmarks),
    "import_donnees": ("import.json", ConfigImport),
}


def _lire_json(chemin: Path) -> dict:
    with chemin.open("r", encoding="utf-8") as fichier:
        return json.load(fichier)


def charger_config(dossier: Path, surcharge: Path | None = None) -> Config:
    """Load every config/*.json file, validate it, and assemble a Config.

    `surcharge` is a folder containing only the keys to override (see
    "Surcharge" in docs/configuration.md) — used by benchmark sweeps and
    tests that need an extreme rule.

    Raises ConfigInvalide, collecting every problem found rather than
    stopping at the first one, so a broken config can be fixed in one pass.
    """
    erreurs: list[str] = []
    sections: dict[str, object] = {}

    for champ, (nom_fichier, classe) in _FICHIERS.items():
        chemin = dossier / nom_fichier
        if not chemin.is_file():
            erreurs.append(f"{nom_fichier}: fichier introuvable dans {dossier}")
            continue

        donnees = _lire_json(chemin)
        if surcharge is not None:
            chemin_surcharge = surcharge / nom_fichier
            if chemin_surcharge.is_file():
                donnees = fusionner(donnees, _lire_json(chemin_surcharge))
        donnees = retirer_notes(donnees)

        try:
            sections[champ] = classe(**donnees)
        except ValidationError as exc:
            for erreur in exc.errors():
                chemin_champ = ".".join(str(partie) for partie in erreur["loc"])
                erreurs.append(f"{nom_fichier}: {chemin_champ}: {erreur['msg']}")

    if erreurs:
        raise ConfigInvalide(erreurs)

    config = Config(**sections)

    erreurs = verifier_coherence(config)
    if erreurs:
        raise ConfigInvalide(erreurs)

    return config
