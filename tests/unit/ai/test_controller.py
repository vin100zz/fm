from random import Random

from core.ai.controller import AIController
from core.ai.valorisation import valeur
from core.config import Config
from core.domain.attributs import Attributs
from core.domain.offre import Offre, TypeReponse
from core.domain.poste import Poste
from tests.unit.world.fabriques_domaine import DATE, des_attributs, un_club, un_joueur

POSTES_442 = [
    Poste.GB, Poste.DL, Poste.DC, Poste.DC, Poste.DR,
    Poste.AILG, Poste.MC, Poste.MC, Poste.AILD, Poste.BU, Poste.BU,
]


def _uniforme(note: int) -> Attributs:
    return des_attributs(**{champ: note for champ in Attributs.__dataclass_fields__})


def test_choisir_composition_delegue_a_selection(cfg: Config) -> None:
    club = un_club(formation_preferee="4-4-2")
    adversaire = un_club(id=2, formation_preferee="4-4-2")
    effectif = [un_joueur(id=i, poste=poste, club_id=club.id, attributs=_uniforme(60)) for i, poste in enumerate(POSTES_442)]

    equipe = AIController().choisir_composition(club, effectif, adversaire, domicile=True, cfg=cfg)
    assert len(equipe.onze) == 11


def test_evaluer_besoins_delegue_a_besoins(cfg: Config) -> None:
    club = un_club(reputation=50)
    assert AIController().evaluer_besoins(club, [], cfg) != []


def test_repondre_offre_delegue_a_mercato(cfg: Config) -> None:
    club = un_club()
    joueur = un_joueur(id=1, poste=Poste.BU, attributs=_uniforme(70))
    prix = valeur(joueur, DATE, cfg)
    offre = Offre(joueur_id=1, club_acheteur_id=2, montant=round(prix * 3), salaire_propose=20_000)

    reponse = AIController().repondre_offre(offre, club, joueur, [joueur], DATE, cfg)
    assert reponse.type is TypeReponse.ACCEPTE


def test_score_offre_delegue_a_mercato(cfg: Config) -> None:
    club = un_club(reputation=60)
    joueur = un_joueur(id=1, poste=Poste.BU, attributs=_uniforme(70))
    score = AIController().score_offre(joueur, club, 30_000, [], DATE, cfg, Random(1))
    assert isinstance(score, float)
