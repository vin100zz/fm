from core.ai.besoins import evaluer_besoins, evaluer_opportunites, niveau_cible, profondeur_utile, projeter_temps_jeu, rang_au_poste
from core.world.note_globale import note_globale
from core.config import Config
from core.domain.attributs import Attributs
from core.domain.besoin import TypeBesoin
from core.domain.poste import Poste
from tests.unit.world.fabriques_domaine import des_attributs, un_club, un_joueur


def _uniforme(note: int) -> Attributs:
    return des_attributs(**{champ: note for champ in Attributs.__dataclass_fields__})


def test_niveau_cible_croit_avec_la_reputation(cfg: Config) -> None:
    petit = un_club(reputation=10)
    grand = un_club(reputation=90)
    assert niveau_cible(grand, cfg) > niveau_cible(petit, cfg)


def test_evaluer_besoins_signale_un_manque_pour_poste_vide(cfg: Config) -> None:
    club = un_club(reputation=50)
    besoins = evaluer_besoins(club, [], cfg)
    assert besoins
    assert all(besoin.type is TypeBesoin.MANQUE for besoin in besoins)
    assert {besoin.poste for besoin in besoins} == {Poste(code) for code in cfg.ia.profil_cible.effectif_par_poste}


def test_evaluer_besoins_signale_un_surplus_au_dela_de_la_profondeur_utile(cfg: Config) -> None:
    club = un_club(reputation=50)
    profondeur = profondeur_utile(Poste.BU, cfg)
    effectif = [un_joueur(id=i, poste=Poste.BU, attributs=_uniforme(60)) for i in range(profondeur + 2)]

    besoins = evaluer_besoins(club, effectif, cfg)
    surplus = [besoin for besoin in besoins if besoin.type is TypeBesoin.SURPLUS and besoin.poste is Poste.BU]
    assert len(surplus) == 2


def test_evaluer_opportunites_signale_un_titulaire_deja_adequat(cfg: Config) -> None:
    club = un_club(reputation=50)
    cible = niveau_cible(club, cfg)
    titulaire = un_joueur(id=1, poste=Poste.BU, attributs=_uniforme(round(cible)))

    opportunites = evaluer_opportunites(club, [titulaire], cfg)

    but = [o for o in opportunites if o.poste is Poste.BU]
    assert len(but) == 1
    assert but[0].type is TypeBesoin.MANQUE
    assert but[0].niveau_attendu == note_globale(titulaire, cfg.attributs) + cfg.ia.profil_cible.marge_amelioration_opportuniste


def test_evaluer_opportunites_ignore_un_poste_vide(cfg: Config) -> None:
    club = un_club(reputation=50)
    opportunites = evaluer_opportunites(club, [], cfg)
    assert opportunites == []


def test_rang_au_poste_ordonne_par_niveau_decroissant(cfg: Config) -> None:
    faible = un_joueur(id=1, poste=Poste.MC, attributs=_uniforme(40))
    fort = un_joueur(id=2, poste=Poste.MC, attributs=_uniforme(80))
    effectif = [faible, fort]

    assert rang_au_poste(fort, effectif, cfg) == 0
    assert rang_au_poste(faible, effectif, cfg) == 1


def test_projeter_temps_jeu_maximal_pour_un_titulaire_clair(cfg: Config) -> None:
    titulaire = un_joueur(id=1, poste=Poste.BU, attributs=_uniforme(80))
    assert projeter_temps_jeu(titulaire, [titulaire], cfg) == 1.0


def test_projeter_temps_jeu_nul_au_dela_de_la_profondeur_utile(cfg: Config) -> None:
    profondeur = profondeur_utile(Poste.BU, cfg)
    effectif = [un_joueur(id=i, poste=Poste.BU, attributs=_uniforme(90 - i)) for i in range(profondeur + 3)]
    dernier = effectif[-1]

    assert projeter_temps_jeu(dernier, effectif, cfg) == 0.0
