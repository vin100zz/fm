from core.config import Config
from core.domain.poste import Poste
from core.world.demographie.cohorte import (
    bucket_de,
    compter_par_bucket_niveau,
    compter_par_nation,
    compter_par_poste,
    corriger,
    corriger_poids,
)
from tests.unit.world.fabriques_domaine import des_attributs, un_joueur


def test_corriger_ne_change_rien_si_cible_egale_observe() -> None:
    assert corriger(cible=120, observe=120, kappa=0.30) == 1.0


def test_corriger_augmente_le_poids_si_sous_represente() -> None:
    assert corriger(cible=200, observe=50, kappa=0.30) > 1.0


def test_corriger_diminue_le_poids_si_sur_represente() -> None:
    assert corriger(cible=50, observe=200, kappa=0.30) < 1.0


def test_corriger_poids_somme_a_un(cfg: Config) -> None:
    cibles = cfg.demographie.cible_postes
    observes = {"GB": 300, "BU": 1}  # tres deforme par rapport a la cible
    corriges = corriger_poids(cibles, observes, kappa=0.30)
    assert abs(sum(corriges.values()) - 1.0) < 1e-9
    assert set(corriges) == set(cibles)


def test_corriger_poids_reequilibre_vers_le_poste_sous_represente(cfg: Config) -> None:
    cibles = cfg.demographie.cible_postes
    # Population de 1000 joueurs a la cible exacte, sauf BU en penurie.
    total = 1000
    observes = {poste: round(part * total) for poste, part in cibles.items()}
    observes["BU"] = 1

    corriges = corriger_poids(cibles, observes, kappa=0.30)
    assert corriges["BU"] > cibles["BU"]


def test_compter_par_poste_retourne_des_comptes_bruts() -> None:
    population = [un_joueur(id=1, poste=Poste.GB), un_joueur(id=2, poste=Poste.BU), un_joueur(id=3, poste=Poste.BU)]
    assert compter_par_poste(population) == {"GB": 1, "BU": 2}


def test_compter_par_poste_population_vide() -> None:
    assert compter_par_poste([]) == {}


def test_compter_par_nation_ignore_les_nations_non_suivies() -> None:
    population = [
        un_joueur(id=1, nationalite="France"),
        un_joueur(id=2, nationalite="France"),
        un_joueur(id=3, nationalite="Bresil"),
    ]
    comptes = compter_par_nation(population, frozenset({"France", "Espagne"}))
    assert comptes == {"France": 2}


def test_bucket_de_trouve_le_bon_intervalle() -> None:
    buckets = [(35, 50), (50, 60), (60, 70)]
    assert bucket_de(55, buckets) == (50, 60)
    assert bucket_de(35, buckets) == (35, 50)


def test_bucket_de_hors_plage_retourne_none() -> None:
    buckets = [(35, 50), (50, 60)]
    assert bucket_de(10, buckets) is None
    assert bucket_de(60, buckets) is None  # borne haute exclusive


def test_compter_par_bucket_niveau(cfg: Config) -> None:
    faible = un_joueur(id=1, attributs=des_attributs(**{c: 40 for c in des_attributs().__dataclass_fields__}))
    fort = un_joueur(id=2, attributs=des_attributs(**{c: 80 for c in des_attributs().__dataclass_fields__}))
    buckets = [(35, 50), (70, 90)]

    comptes = compter_par_bucket_niveau([faible, fort], buckets, cfg.attributs)
    assert comptes == {(35, 50): 1, (70, 90): 1}
