from random import Random

from core.ai.mercato import repondre_offre, score_offre, surplus
from core.ai.valorisation import valeur
from core.config import Config
from core.domain.attributs import Attributs
from core.domain.offre import Offre, TypeReponse
from core.domain.poste import Poste
from tests.unit.world.fabriques_domaine import DATE, des_attributs, un_club, un_joueur


def _uniforme(note: int) -> Attributs:
    return des_attributs(**{champ: note for champ in Attributs.__dataclass_fields__})


def test_surplus_nul_pour_le_seul_titulaire(cfg: Config) -> None:
    titulaire = un_joueur(id=1, poste=Poste.BU, attributs=_uniforme(70))
    assert surplus(titulaire, [titulaire], cfg) == 0.0


def test_surplus_maximal_au_dela_de_la_profondeur_utile(cfg: Config) -> None:
    from core.ai.besoins import profondeur_utile

    profondeur = profondeur_utile(Poste.BU, cfg)
    effectif = [un_joueur(id=i, poste=Poste.BU, attributs=_uniforme(90 - i)) for i in range(profondeur + 3)]
    dernier = effectif[-1]
    assert surplus(dernier, effectif, cfg) == 1.0


def test_repondre_offre_accepte_au_dessus_du_seuil(cfg: Config) -> None:
    club = un_club()
    joueur = un_joueur(id=1, poste=Poste.BU, attributs=_uniforme(70))
    prix = valeur(joueur, DATE, cfg)
    offre = Offre(joueur_id=1, club_acheteur_id=2, montant=round(prix * 3), salaire_propose=20_000)

    reponse = repondre_offre(offre, club, joueur, [joueur], DATE, cfg)
    assert reponse.type is TypeReponse.ACCEPTE


def test_repondre_offre_refuse_en_dessous_du_seuil(cfg: Config) -> None:
    club = un_club()
    joueur = un_joueur(id=1, poste=Poste.BU, attributs=_uniforme(70))
    prix = valeur(joueur, DATE, cfg)
    offre = Offre(joueur_id=1, club_acheteur_id=2, montant=round(prix * 0.1), salaire_propose=20_000)

    reponse = repondre_offre(offre, club, joueur, [joueur], DATE, cfg)
    assert reponse.type is TypeReponse.REFUSE


def test_repondre_offre_surplus_reduit_le_seuil_de_vente(cfg: Config) -> None:
    from core.ai.besoins import profondeur_utile

    club = un_club()
    profondeur = profondeur_utile(Poste.BU, cfg)
    effectif = [un_joueur(id=i, poste=Poste.BU, attributs=_uniforme(70)) for i in range(profondeur + 2)]
    cible = effectif[-1]  # surplus == 1.0
    titulaire = effectif[0]  # surplus == 0.0

    prix = valeur(cible, DATE, cfg)
    # Entre le seuil du surplus (1.32x, cf. 1.35 - 0.25*1.0, patience 0.5) et
    # celui du titulaire (1.62x, surplus nul) : accepte pour l'un, pas l'autre.
    offre_moyenne = Offre(joueur_id=cible.id, club_acheteur_id=2, montant=round(prix * 1.45), salaire_propose=20_000)

    reponse_surplus = repondre_offre(offre_moyenne, club, cible, effectif, DATE, cfg)
    reponse_titulaire = repondre_offre(offre_moyenne, club, titulaire, effectif, DATE, cfg)

    assert reponse_surplus.type is TypeReponse.ACCEPTE
    assert reponse_titulaire.type is not TypeReponse.ACCEPTE


def test_score_offre_deterministe_avec_le_meme_rng(cfg: Config) -> None:
    club = un_club(reputation=60)
    joueur = un_joueur(id=1, poste=Poste.BU, attributs=_uniforme(70))
    score_a = score_offre(joueur, club, 30_000, [], DATE, cfg, Random(7))
    score_b = score_offre(joueur, club, 30_000, [], DATE, cfg, Random(7))
    assert score_a == score_b


def test_score_offre_croit_avec_le_salaire_propose(cfg: Config) -> None:
    club = un_club(reputation=60)
    joueur = un_joueur(id=1, poste=Poste.BU, attributs=_uniforme(70))
    faible = score_offre(joueur, club, 1_000, [], DATE, cfg, Random(1))
    fort = score_offre(joueur, club, 1_000_000_000, [], DATE, cfg, Random(1))
    assert fort > faible
