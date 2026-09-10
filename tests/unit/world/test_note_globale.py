import pytest

from core.config import Config
from core.domain.poste import Poste
from core.world.note_globale import note_globale
from tests.unit.world.fabriques_domaine import des_attributs, un_joueur


def test_attributs_uniformes_donnent_cette_valeur(cfg: Config) -> None:
    joueur = un_joueur(poste=Poste.MC, attributs=des_attributs())  # tout a 50

    assert note_globale(joueur, cfg.attributs) == pytest.approx(50.0)


def test_un_attribut_fort_pese_selon_son_poids(cfg: Config) -> None:
    base = un_joueur(poste=Poste.MC, attributs=des_attributs())
    avec_passe_haute = un_joueur(poste=Poste.MC, attributs=des_attributs(passe=100))

    assert note_globale(avec_passe_haute, cfg.attributs) > note_globale(base, cfg.attributs)


def test_meme_attribut_pese_differemment_selon_le_poste(cfg: Config) -> None:
    # note_globale.GB ne pese pas la finition ; note_globale.BU la pese fort (0.38)
    gardien = un_joueur(poste=Poste.GB, attributs=des_attributs(finition=100))
    attaquant = un_joueur(poste=Poste.BU, attributs=des_attributs(finition=100))

    gardien_base = un_joueur(poste=Poste.GB, attributs=des_attributs())
    attaquant_base = un_joueur(poste=Poste.BU, attributs=des_attributs())

    assert note_globale(gardien, cfg.attributs) == pytest.approx(note_globale(gardien_base, cfg.attributs))
    assert note_globale(attaquant, cfg.attributs) > note_globale(attaquant_base, cfg.attributs)
