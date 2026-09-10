from random import Random

from core.config import Config
from core.domain.geometrie import Couloir, Zone
from core.domain.poste import Poste
from core.engine.cartons import determiner_carton
from core.engine.equipe import PositionOnze
from core.engine.implication import construire_tables_implication
from tests.unit.world.fabriques_domaine import un_joueur


def _onze_avec_gardien() -> tuple[PositionOnze, ...]:
    postes = [Poste.GB, Poste.DC, Poste.DC, Poste.DL, Poste.DR, Poste.MDC, Poste.MC, Poste.MC, Poste.MOC, Poste.AILG, Poste.BU]
    return tuple(PositionOnze(poste=poste, joueur=un_joueur(id=i, poste=poste)) for i, poste in enumerate(postes))


def test_le_gardien_nest_jamais_le_fauteur(cfg: Config) -> None:
    tables = construire_tables_implication(cfg.implications)
    onze = _onze_avec_gardien()
    rng = Random(1)

    for _ in range(500):
        resultat = determiner_carton(Zone.DEFENSE, Couloir.AXE, onze, tables, cfg.moteur.cartons, rng)
        if resultat is not None:
            fauteur, _couleur = resultat
            assert fauteur.poste is not Poste.GB


def test_onze_uniquement_gardien_ne_plante_pas(cfg: Config) -> None:
    tables = construire_tables_implication(cfg.implications)
    onze = (PositionOnze(poste=Poste.GB, joueur=un_joueur(id=1, poste=Poste.GB)),)

    resultat = determiner_carton(Zone.DEFENSE, Couloir.AXE, onze, tables, cfg.moteur.cartons, Random(1))

    assert resultat is None
