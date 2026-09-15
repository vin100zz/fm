from core.ai.selection import _selectionner_onze, choisir_composition, decider_remplacement
from core.config import Config
from core.domain.attributs import Attributs
from core.domain.date import Date
from core.domain.etat_joueur import Blessure, Gravite
from core.domain.etat_match import EtatMatch
from core.domain.poste import Poste
from tests.unit.world.fabriques_domaine import DATE, des_attributs, un_club, un_joueur

POSTES_442 = [
    Poste.GB, Poste.DL, Poste.DC, Poste.DC, Poste.DR,
    Poste.AILG, Poste.MC, Poste.MC, Poste.AILD, Poste.BU, Poste.BU,
]


def _uniforme(note: int) -> Attributs:
    return des_attributs(**{champ: note for champ in Attributs.__dataclass_fields__})


def _effectif_442(club_id: int, fatigue: float = 1.0) -> list:
    return [
        un_joueur(id=i, poste=poste, club_id=club_id, attributs=_uniforme(60), fatigue=fatigue)
        for i, poste in enumerate(POSTES_442)
    ]


def test_choisir_composition_ecarte_les_blesses(cfg: Config) -> None:
    club = un_club(formation_preferee="4-4-2")
    adversaire = un_club(id=2, formation_preferee="4-4-2")
    effectif = _effectif_442(club.id)
    effectif[9].blessure = Blessure(date_debut=DATE, date_fin=Date(2026, 8, 20), gravite=Gravite.LEGERE, description="test")
    remplacant = un_joueur(id=500, poste=Poste.BU, club_id=club.id, attributs=_uniforme(60))
    effectif.append(remplacant)

    equipe = choisir_composition(club, effectif, adversaire, domicile=True, cfg=cfg)

    joueurs_retenus = {position.joueur.id for position in equipe.onze}
    assert 9 not in joueurs_retenus
    assert 500 in joueurs_retenus


def test_choisir_composition_complete_avec_des_dummy_si_effectif_trop_petit(cfg: Config) -> None:
    """Repere en production (2026-09-11) : un effectif appauvri par les
    renouvellements/agents libres/demarchages tombe sous 11 joueurs
    disponibles -> IndexError sur candidats[0]. `_joueur_dummy` complete
    desormais le onze avec des joueurs de secours transitoires plutot
    que de planter (demande explicite de l'utilisateur)."""
    club = un_club(formation_preferee="4-4-2")
    adversaire = un_club(id=2, formation_preferee="4-4-2")
    effectif = [un_joueur(id=i, poste=Poste.MC, club_id=club.id, attributs=_uniforme(60)) for i in range(5)]

    equipe = choisir_composition(club, effectif, adversaire, domicile=True, cfg=cfg)

    assert len(equipe.onze) == 11
    dummies = [position.joueur for position in equipe.onze if position.joueur.nom == "Dummy"]
    assert len(dummies) == 6  # 11 slots, 5 vrais joueurs
    assert len({d.id for d in dummies}) == 6  # chacun un id distinct
    for dummy in dummies:
        assert dummy.attributs.valeur("passe") == round(60 * (1 - cfg.ia.selection.reduction_niveau_dummy))


def test_selectionner_onze_cree_des_dummy_si_aucun_joueur_disponible(cfg: Config) -> None:
    onze = _selectionner_onze([], "4-4-2", cfg.ia.selection, cfg, effectif_reference=[])
    assert len(onze) == 11
    assert all(position.joueur.nom == "Dummy" for position in onze)


def test_hauteur_bloc_plus_haute_a_domicile_et_contre_plus_faible(cfg: Config) -> None:
    club = un_club(formation_preferee="4-4-2", reputation=70)
    adversaire = un_club(id=2, formation_preferee="4-4-2", reputation=30)
    effectif = _effectif_442(club.id)

    domicile = choisir_composition(club, effectif, adversaire, domicile=True, cfg=cfg)
    exterieur = choisir_composition(club, effectif, adversaire, domicile=False, cfg=cfg)

    assert domicile.hauteur_bloc > exterieur.hauteur_bloc


def test_decider_remplacement_rien_si_pas_de_banc(cfg: Config) -> None:
    onze = tuple(un_joueur(id=i, poste=poste, attributs=_uniforme(60)) for i, poste in enumerate(POSTES_442))
    etat = EtatMatch(minute=60, buts_pour=0, buts_contre=0, onze_actuel=onze, banc=(), remplacements_effectues=0)

    assert decider_remplacement(etat, frozenset(), remplacements_max=5, cfg=cfg) is None


def test_decider_remplacement_rien_si_quota_atteint(cfg: Config) -> None:
    onze = tuple(un_joueur(id=i, poste=poste, attributs=_uniforme(60), fatigue=0.1) for i, poste in enumerate(POSTES_442))
    banc = (un_joueur(id=100, poste=Poste.BU, attributs=_uniforme(60)),)
    etat = EtatMatch(minute=60, buts_pour=0, buts_contre=0, onze_actuel=onze, banc=banc, remplacements_effectues=5)

    assert decider_remplacement(etat, frozenset(), remplacements_max=5, cfg=cfg) is None


def test_decider_remplacement_priorise_le_blesse(cfg: Config) -> None:
    onze = [un_joueur(id=i, poste=poste, attributs=_uniforme(60), fatigue=0.1) for i, poste in enumerate(POSTES_442)]
    onze[9].blessure = Blessure(date_debut=DATE, date_fin=Date(2026, 8, 20), gravite=Gravite.LEGERE, description="test")
    banc = (un_joueur(id=100, poste=Poste.BU, attributs=_uniforme(55)),)
    etat = EtatMatch(
        minute=60, buts_pour=0, buts_contre=0, onze_actuel=tuple(onze), banc=banc, remplacements_effectues=0
    )

    remplacement = decider_remplacement(etat, frozenset(), remplacements_max=5, cfg=cfg)

    assert remplacement is not None
    assert remplacement.joueur_sortant_id == 9
    assert remplacement.joueur_entrant_id == 100
    assert remplacement.motif == "blessure"


def test_decider_remplacement_sort_le_joueur_le_plus_fatigue(cfg: Config) -> None:
    onze = [un_joueur(id=i, poste=poste, attributs=_uniforme(60), fatigue=0.9) for i, poste in enumerate(POSTES_442)]
    onze[9] = un_joueur(id=9, poste=Poste.BU, attributs=_uniforme(60), fatigue=0.1)  # sous le seuil
    banc = (un_joueur(id=100, poste=Poste.BU, attributs=_uniforme(58)),)
    etat = EtatMatch(
        minute=60, buts_pour=0, buts_contre=0, onze_actuel=tuple(onze), banc=banc, remplacements_effectues=0
    )

    remplacement = decider_remplacement(etat, frozenset(), remplacements_max=5, cfg=cfg)

    assert remplacement is not None
    assert remplacement.joueur_sortant_id == 9
    assert remplacement.motif == "fatigue"
