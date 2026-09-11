"""Process-global in-memory game state — CLAUDE.md: "état en mémoire
dans le processus", no database. One `EtatServeur` per running API
process; route handlers read it through `obtenir_etat` (a FastAPI
dependency).
"""

from dataclasses import dataclass
from pathlib import Path
from random import Random

from core.config import Config, charger_config
from core.domain.date import Date
from core.domain.journal import EvenementJour
from core.domain.monde import Monde
from core.world.importation import importer_monde
from core.world.saison import initialiser_saison

RACINE_PROJET = Path(__file__).resolve().parent.parent.parent
DOSSIER_CONFIG = RACINE_PROJET / "config"
DOSSIER_DONNEES = RACINE_PROJET / "data"

# Pas de calendrier reel ("Date" est une date de jeu — CLAUDE.md) : une
# nouvelle partie demarre toujours a la meme date, comme la graine.
DATE_DEBUT_PARTIE = Date(2026, 8, 10)
GRAINE_PARTIE = 1


@dataclass
class EtatServeur:
    cfg: Config
    monde: Monde
    rng: Random
    avertissements_import: list[str]
    dernier_journal: list[EvenementJour]


_etat: EtatServeur | None = None


def initialiser() -> EtatServeur:
    global _etat
    cfg = charger_config(DOSSIER_CONFIG)
    rng = Random(GRAINE_PARTIE)
    monde, avertissements = importer_monde(DOSSIER_DONNEES, cfg, DATE_DEBUT_PARTIE, GRAINE_PARTIE, rng)
    initialiser_saison(monde, cfg, rng)
    _etat = EtatServeur(cfg=cfg, monde=monde, rng=rng, avertissements_import=avertissements, dernier_journal=[])
    return _etat


def obtenir_etat() -> EtatServeur:
    if _etat is None:
        raise RuntimeError("Etat serveur non initialise — appeler initialiser() au demarrage de l'application")
    return _etat
