import json
import shutil
from pathlib import Path

import pytest

DOSSIER_CONFIG_REEL = Path(__file__).resolve().parents[3] / "config"


@pytest.fixture
def dossier_config() -> Path:
    """The real config/ folder shipped with the project."""
    return DOSSIER_CONFIG_REEL


@pytest.fixture
def config_modifiable(tmp_path: Path) -> Path:
    """A writable copy of the real config/ folder, for tests that break one file."""
    copie = tmp_path / "config"
    shutil.copytree(DOSSIER_CONFIG_REEL, copie)
    return copie


def lire(chemin: Path) -> dict:
    with chemin.open("r", encoding="utf-8") as fichier:
        return json.load(fichier)


def ecrire(chemin: Path, donnees: dict) -> None:
    with chemin.open("w", encoding="utf-8") as fichier:
        json.dump(donnees, fichier, ensure_ascii=False, indent=2)
