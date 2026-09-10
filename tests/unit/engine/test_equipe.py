from core.config import Config
from core.domain.joueur import Joueur
from core.domain.poste import Poste
from core.engine.equipe import equipe_depuis_effectif
from tests.unit.world.fabriques_domaine import des_attributs, un_joueur


def des_joueurs(club_id: int, poste: Poste, n: int, **overrides) -> dict[int, Joueur]:
    # id offset par club_id : des ids qui se chevauchent entre deux clubs
    # feraient disparaitre silencieusement des joueurs en fusionnant les dicts.
    return {
        club_id * 1000 + i: un_joueur(
            id=club_id * 1000 + i, club_id=club_id, poste=poste, attributs=des_attributs(**overrides)
        )
        for i in range(n)
    }


def test_attaquants_forts_et_defenseurs_faibles_donnent_plus_de_force_offensive(cfg: Config) -> None:
    # Une force uniforme (meme poste, meme note partout) ne peut jamais
    # differencier attaque/defense : la moyenne ponderee d'une valeur
    # constante vaut cette valeur, quels que soient les poids. Il faut
    # une composition asymetrique pour observer un ecart.
    attaquants = des_joueurs(
        1, Poste.BU, 6, finition=95, sang_froid=95, technique=95, jeu_tete=95, vitesse=95
    )
    defenseurs = {
        100 + i: un_joueur(
            id=100 + i, club_id=1, poste=Poste.DC,
            attributs=des_attributs(tacle=15, placement=15, jeu_tete=15, vitesse=15, passe=15),
        )
        for i in range(5)
    }

    equipe = equipe_depuis_effectif(1, {**attaquants, **defenseurs}, cfg)

    assert equipe.force_attaque > equipe.force_defense


def test_effectif_tout_en_defense_a_plus_de_force_defensive_que_offensive(cfg: Config) -> None:
    joueurs = des_joueurs(1, Poste.DC, 11)

    equipe = equipe_depuis_effectif(1, joueurs, cfg)

    assert equipe.force_defense > equipe.force_attaque


def test_effectif_vide_retourne_le_plancher(cfg: Config) -> None:
    equipe = equipe_depuis_effectif(1, {}, cfg)

    assert equipe.force_attaque == cfg.attributs.bornes.min
    assert equipe.force_defense == cfg.attributs.bornes.min


def test_seuls_les_meilleurs_onze_comptent(cfg: Config) -> None:
    forts = des_joueurs(1, Poste.MC, 11, passe=90, technique=90, vision=90, endurance=90, tacle=90)
    faibles = {
        100 + i: un_joueur(id=100 + i, club_id=1, poste=Poste.MC, attributs=des_attributs(passe=1))
        for i in range(20)
    }

    equipe_avec_faibles = equipe_depuis_effectif(1, {**forts, **faibles}, cfg)
    equipe_sans_faibles = equipe_depuis_effectif(1, forts, cfg)

    assert equipe_avec_faibles.force_attaque == equipe_sans_faibles.force_attaque
    assert equipe_avec_faibles.force_defense == equipe_sans_faibles.force_defense


def test_seul_le_club_demande_est_pris_en_compte(cfg: Config) -> None:
    joueurs_club_1 = des_joueurs(1, Poste.MC, 11)
    joueurs_club_2 = des_joueurs(2, Poste.MC, 11, passe=99, technique=99, vision=99)

    equipe_1_seule = equipe_depuis_effectif(1, joueurs_club_1, cfg)
    equipe_1_avec_club_2_present = equipe_depuis_effectif(1, {**joueurs_club_1, **joueurs_club_2}, cfg)

    assert equipe_1_seule == equipe_1_avec_club_2_present
