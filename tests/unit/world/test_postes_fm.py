import pytest

from core.domain.poste import Poste
from core.world.importation.erreurs import ImportInvalide
from core.world.importation.postes_fm import parser_postes

AFFINITE = 0.6


def test_gardien_simple() -> None:
    principal, secondaires = parser_postes("GK", AFFINITE)
    assert principal is Poste.GB
    assert secondaires == {}


def test_poste_simple_sans_cote() -> None:
    principal, secondaires = parser_postes("DM", AFFINITE)
    assert principal is Poste.MDC
    assert secondaires == {}


def test_poste_simple_avec_cote() -> None:
    principal, secondaires = parser_postes("D C", AFFINITE)
    assert principal is Poste.DC


def test_plusieurs_cotes_dans_un_groupe() -> None:
    # "AM RL" -> AM,R puis AM,L -> AILD principal, AILG secondaire
    principal, secondaires = parser_postes("AM RL", AFFINITE)
    assert principal is Poste.AILD
    assert secondaires == {Poste.AILG: AFFINITE}


def test_groupes_separes_par_virgule() -> None:
    principal, secondaires = parser_postes("M C, ST", AFFINITE)
    assert principal is Poste.MC
    assert secondaires == {Poste.BU: AFFINITE}


def test_roles_alternatifs_avec_slash() -> None:
    # "D/WB L" -> D,L et WB,L pointent tous les deux vers DL -> dedoublonne
    principal, secondaires = parser_postes("D/WB L", AFFINITE)
    assert principal is Poste.DL
    assert secondaires == {}


def test_cas_complexe_reel() -> None:
    # tire de data/players.csv (Harry Kane)
    principal, secondaires = parser_postes("AM/F C", AFFINITE)
    assert principal is Poste.MOC
    assert secondaires == {Poste.BU: AFFINITE}


def test_cas_complexe_avec_trois_groupes() -> None:
    principal, secondaires = parser_postes("D/WB R, DM, AM RC", AFFINITE)
    assert principal is Poste.DR
    assert secondaires == {Poste.MDC: AFFINITE, Poste.AILD: AFFINITE, Poste.MOC: AFFINITE}


def test_position_non_reconnue_leve_import_invalide() -> None:
    with pytest.raises(ImportInvalide):
        parser_postes("XYZ", AFFINITE)
