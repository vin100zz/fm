from core.config import Config
from core.domain.club import StatutClub
from core.domain.joueur import Joueur
from core.domain.poste import Poste
from core.world.importation.limitation import limiter_effectifs_actifs
from tests.unit.world.fabriques_domaine import des_attributs, un_club, un_joueur


def test_effectif_sous_la_limite_nest_pas_touche(cfg: Config) -> None:
    club = un_club()
    joueurs = {j.id: j for j in (un_joueur(id=i, club_id=club.id) for i in range(5))}

    avertissements = limiter_effectifs_actifs(joueurs, {club.id: club}, cfg.attributs, effectif_max=30)

    assert avertissements == []
    assert all(joueur.club_id == club.id for joueur in joueurs.values())


def test_garde_les_meilleurs_et_libere_le_reste(cfg: Config) -> None:
    club = un_club()
    # BU pese fort la finition (config/attributs.json -> note_globale.BU) :
    # classer par finition decroissante donne un ordre sans ambiguite.
    joueurs: dict[int, Joueur] = {}
    for i, finition in enumerate([90, 80, 70, 60, 50]):
        joueur = un_joueur(id=i, club_id=club.id, poste=Poste.BU, attributs=des_attributs(finition=finition))
        joueurs[joueur.id] = joueur

    avertissements = limiter_effectifs_actifs(joueurs, {club.id: club}, cfg.attributs, effectif_max=3)

    gardes = {jid for jid, joueur in joueurs.items() if joueur.club_id == club.id}
    assert gardes == {0, 1, 2}
    assert joueurs[3].club_id is None
    assert joueurs[3].contrat is None
    assert joueurs[4].club_id is None
    assert len(avertissements) == 1
    assert "5 a 3" in avertissements[0]


def test_ignore_les_clubs_dormants(cfg: Config) -> None:
    club = un_club(statut=StatutClub.DORMANT)
    joueurs = {j.id: j for j in (un_joueur(id=i, club_id=club.id) for i in range(40))}

    avertissements = limiter_effectifs_actifs(joueurs, {club.id: club}, cfg.attributs, effectif_max=30)

    assert avertissements == []
    assert all(joueur.club_id == club.id for joueur in joueurs.values())


def test_ignore_les_agents_libres() -> None:
    joueurs = {1: un_joueur(id=1, club_id=None, contrat=None)}
    avertissements = limiter_effectifs_actifs(joueurs, {}, cfg_attributs=None, effectif_max=0)  # type: ignore[arg-type]

    assert avertissements == []
    assert joueurs[1].club_id is None
