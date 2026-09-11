from random import Random

from core.world.demographie.identite import construire_pools_noms, tirer_identite
from tests.unit.world.fabriques_domaine import un_joueur

NATIONS_SIMULEES = frozenset({"France", "Espagne"})


def test_construire_pools_noms_groupe_par_nation_simulee() -> None:
    population = [
        un_joueur(id=1, nom="Martin", prenom="Paul", nationalite="France"),
        un_joueur(id=2, nom="Garcia", prenom="Luis", nationalite="Espagne"),
        un_joueur(id=3, nom="Silva", prenom="Joao", nationalite="Bresil"),
    ]
    pools = construire_pools_noms(population, NATIONS_SIMULEES)

    assert pools.par_nation == {"France": [("Martin", "Paul")], "Espagne": [("Garcia", "Luis")]}
    assert pools.exterieur == [("Bresil", "Silva", "Joao")]


def test_construire_pools_noms_ignore_les_mononymes_sans_nom() -> None:
    population = [un_joueur(id=1, nom="", prenom="", nationalite="France")]
    pools = construire_pools_noms(population, NATIONS_SIMULEES)
    assert pools.par_nation == {}


def test_tirer_identite_pioche_dans_la_nation_ciblee() -> None:
    population = [un_joueur(id=1, nom="Martin", prenom="Paul", nationalite="France")]
    pools = construire_pools_noms(population, NATIONS_SIMULEES)

    nationalite, nom, prenom = tirer_identite("France", pools, frozenset(), Random(1), tentatives_max=5)
    assert (nationalite, nom, prenom) == ("France", "Martin", "Paul")


def test_tirer_identite_retombe_sur_l_exterieur_si_nation_inconnue() -> None:
    population = [un_joueur(id=1, nom="Silva", prenom="Joao", nationalite="Bresil")]
    pools = construire_pools_noms(population, NATIONS_SIMULEES)

    nationalite, nom, prenom = tirer_identite(None, pools, frozenset(), Random(1), tentatives_max=5)
    assert (nationalite, nom, prenom) == ("Bresil", "Silva", "Joao")


def test_tirer_identite_redessine_sur_collision_puis_abandonne() -> None:
    population = [un_joueur(id=1, nom="Martin", prenom="Paul", nationalite="France")]
    pools = construire_pools_noms(population, NATIONS_SIMULEES)
    deja_utilises = frozenset({("Martin", "Paul")})

    # Un seul nom possible dans le pool : la collision persiste, mais la
    # fonction rend la main apres tentatives_max plutot que de boucler.
    resultat = tirer_identite("France", pools, deja_utilises, Random(1), tentatives_max=3)
    assert resultat == ("France", "Martin", "Paul")
