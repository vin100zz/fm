from core.config import Config
from core.domain.joueur import Joueur
from core.domain.poste import Poste
from core.engine.equipe import composition_depuis_effectif
from tests.unit.world.fabriques_domaine import un_joueur

_POSTES = [
    Poste.GB, Poste.GB, Poste.DC, Poste.DC, Poste.DC, Poste.DL, Poste.DR,
    Poste.MDC, Poste.MC, Poste.MC, Poste.MOC, Poste.AILG, Poste.AILD, Poste.BU, Poste.BU,
]


def un_effectif_varie(club_id: int) -> dict[int, Joueur]:
    return {
        club_id * 1000 + i: un_joueur(id=club_id * 1000 + i, club_id=club_id, poste=poste)
        for i, poste in enumerate(_POSTES)
    }


def test_onze_complet_sans_doublon(cfg: Config) -> None:
    joueurs = un_effectif_varie(1)

    equipe = composition_depuis_effectif(1, joueurs, "4-4-2", 0.0, cfg)

    assert len(equipe.onze) == 11
    ids = [position.joueur.id for position in equipe.onze]
    assert len(set(ids)) == 11


def test_respecte_les_postes_de_la_formation(cfg: Config) -> None:
    joueurs = un_effectif_varie(1)

    equipe = composition_depuis_effectif(1, joueurs, "4-4-2", 0.0, cfg)

    postes_slots = [position.poste.value for position in equipe.onze]
    assert postes_slots == cfg.formations.formations["4-4-2"]


def test_formation_et_hauteur_bloc_sont_conservees(cfg: Config) -> None:
    joueurs = un_effectif_varie(1)

    equipe = composition_depuis_effectif(1, joueurs, "4-3-3", 0.4, cfg)

    assert equipe.formation == "4-3-3"
    assert equipe.hauteur_bloc == 0.4


def test_seul_club_id_demande_est_utilise(cfg: Config) -> None:
    joueurs = {**un_effectif_varie(1), **un_effectif_varie(2)}

    equipe = composition_depuis_effectif(1, joueurs, "4-4-2", 0.0, cfg)

    assert all(position.joueur.club_id == 1 for position in equipe.onze)
