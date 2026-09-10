from pathlib import Path

import pytest

from core.config import Config, charger_config

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_CONFIG_REEL = RACINE / "config"
DOSSIER_DONNEES_REEL = RACINE / "data"


@pytest.fixture(scope="session")
def dossier_config() -> Path:
    """The real config/ folder shipped with the project."""
    return DOSSIER_CONFIG_REEL


@pytest.fixture(scope="session")
def dossier_donnees() -> Path:
    """The real data/ folder shipped with the project (data/clubs.csv, data/players.csv)."""
    return DOSSIER_DONNEES_REEL


@pytest.fixture(scope="session")
def cfg(dossier_config: Path) -> Config:
    """The real config, loaded once per test session — config loading is
    itself tested in tests/unit/config/, no need to re-validate it here.
    """
    return charger_config(dossier_config)
