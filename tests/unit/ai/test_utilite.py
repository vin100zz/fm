from core.ai.utilite import utilite
from core.config import Config
from core.domain.attributs import Attributs
from core.domain.poste import Poste
from tests.unit.world.fabriques_domaine import DATE, des_attributs, un_club, un_joueur


def _uniforme(note: int) -> Attributs:
    return des_attributs(**{champ: note for champ in Attributs.__dataclass_fields__})


def test_utilite_positive_pour_un_joueur_meilleur_que_l_effectif(cfg: Config) -> None:
    club = un_club(formation_preferee="4-4-2")
    postes_formation = [
        Poste.GB, Poste.DL, Poste.DC, Poste.DC, Poste.DR,
        Poste.AILG, Poste.MC, Poste.MC, Poste.AILD, Poste.BU, Poste.BU,
    ]
    effectif = [un_joueur(id=i, poste=poste, attributs=_uniforme(50)) for i, poste in enumerate(postes_formation)]
    excellent_attaquant = un_joueur(id=999, poste=Poste.BU, attributs=_uniforme(90))

    assert utilite(excellent_attaquant, club, effectif, DATE, cfg) > 0


def test_utilite_marginale_nulle_pour_un_poste_deja_sature(cfg: Config) -> None:
    """A club whose starting keeper already outclasses the candidate gets
    zero utility from a redundant backup — docs/ia-gestion.md's "un club
    avec trois excellents gardiens tire une utilité quasi nulle d'un
    quatrième".
    """
    club = un_club(formation_preferee="4-4-2")
    postes_formation = [
        Poste.GB, Poste.DL, Poste.DC, Poste.DC, Poste.DR,
        Poste.AILG, Poste.MC, Poste.MC, Poste.AILD, Poste.BU, Poste.BU,
    ]
    effectif = [un_joueur(id=i, poste=poste, attributs=_uniforme(60)) for i, poste in enumerate(postes_formation)]
    effectif[0] = un_joueur(id=0, poste=Poste.GB, attributs=_uniforme(85))
    effectif.append(un_joueur(id=100, poste=Poste.GB, attributs=_uniforme(70)))

    quatrieme_gardien = un_joueur(id=999, poste=Poste.GB, attributs=_uniforme(70))

    assert utilite(quatrieme_gardien, club, effectif, DATE, cfg) == 0.0
