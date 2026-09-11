from collections import Counter
from random import Random

from core.config import Config
from core.domain.date import Date
from core.domain.poste import Poste
from core.world.demographie.generation import (
    generer_regen,
    nationalites_simulees,
    parametres_potentiel,
    promouvoir_centre_formation,
    tirer_age,
    tirer_nation,
    tirer_niveau_actuel,
    tirer_poste,
    tirer_potentiel,
)
from core.world.demographie.identite import construire_pools_noms
from tests.unit.world.fabriques_domaine import un_club, un_joueur

DATE = Date(2026, 8, 10)


def _pools(cfg: Config):
    nats = nationalites_simulees(cfg)
    population = [
        un_joueur(id=i, nom=f"Nom{i}", prenom=f"Prenom{i}", nationalite=nation)
        for i, nation in enumerate(list(nats) * 20 + ["Bresil"] * 20)
    ]
    return construire_pools_noms(population, nats)


def test_nationalites_simulees_correspond_aux_5_championnats(cfg: Config) -> None:
    assert nationalites_simulees(cfg) == {"France", "Espagne", "Italie", "Angleterre", "Allemagne"}


def test_tirer_nation_respecte_le_poids_total_configure(cfg: Config) -> None:
    rng = Random(1)
    tirages = [tirer_nation(cfg, rng) for _ in range(20_000)]
    part_ligues = sum(1 for nation in tirages if nation is not None) / len(tirages)
    assert abs(part_ligues - cfg.demographie.nations.poids_total_ligues_simulees) < 0.02


def test_tirer_nation_ne_retourne_que_les_5_nations_ou_none(cfg: Config) -> None:
    rng = Random(1)
    tirages = {tirer_nation(cfg, rng) for _ in range(2000)}
    assert tirages <= nationalites_simulees(cfg) | {None}


def test_parametres_potentiel_nation_inconnue_utilise_la_moyenne(cfg: Config) -> None:
    cfg_gen = cfg.demographie.generation
    assert parametres_potentiel(None, cfg) == (cfg_gen.beta_alpha_nation_moyenne, cfg_gen.beta_beta_nation_moyenne)


def test_parametres_potentiel_varie_selon_la_force_du_pays(cfg: Config) -> None:
    multiplicateurs = cfg.ia.budgets.revenus.multiplicateur_pays
    forte = max(multiplicateurs, key=multiplicateurs.get)
    faible = min(multiplicateurs, key=multiplicateurs.get)
    nation_forte = next(c.nationalite_source for c in cfg.monde.competitions_simulees if c.pays == forte)
    nation_faible = next(c.nationalite_source for c in cfg.monde.competitions_simulees if c.pays == faible)

    alpha_forte, beta_forte = parametres_potentiel(nation_forte, cfg)
    alpha_faible, beta_faible = parametres_potentiel(nation_faible, cfg)

    assert alpha_forte > alpha_faible
    assert beta_forte < beta_faible


def test_tirer_potentiel_reste_dans_les_bornes_configurees(cfg: Config) -> None:
    cfg_gen = cfg.demographie.generation
    rng = Random(1)
    for _ in range(500):
        potentiel = tirer_potentiel(cfg_gen.beta_alpha_nation_moyenne, cfg_gen.beta_beta_nation_moyenne, cfg, rng)
        assert cfg_gen.potentiel_min <= potentiel <= cfg_gen.potentiel_min + cfg_gen.potentiel_amplitude


def test_tirer_poste_respecte_les_postes_de_la_cible(cfg: Config) -> None:
    rng = Random(1)
    tires = {tirer_poste(cfg, rng) for _ in range(500)}
    assert tires <= {Poste(code) for code in cfg.demographie.cible_postes}


def test_tirer_poste_favorise_le_poids_le_plus_fort(cfg: Config) -> None:
    poids = {"GB": 0.9, "BU": 0.1}
    rng = Random(1)
    tirages = Counter(tirer_poste(cfg, rng, poids).value for _ in range(2000))
    assert tirages["GB"] > tirages["BU"]


def test_tirer_age_dans_la_plage_configuree(cfg: Config) -> None:
    cfg_gen = cfg.demographie.generation
    rng = Random(1)
    for _ in range(200):
        age = tirer_age(cfg, rng)
        assert cfg_gen.age_min <= age <= cfg_gen.age_max


def test_tirer_niveau_actuel_croit_avec_le_potentiel(cfg: Config) -> None:
    rng_a, rng_b = Random(1), Random(1)
    faible = tirer_niveau_actuel(potentiel=40, age=17, cfg=cfg, rng=rng_a)
    fort = tirer_niveau_actuel(potentiel=90, age=17, cfg=cfg, rng=rng_b)
    assert fort > faible


class TestGenererRegen:
    def test_produit_un_joueur_coherent(self, cfg: Config) -> None:
        pools = _pools(cfg)
        rng = Random(1)
        joueur = generer_regen(id=99999, club_id=None, date_actuelle=DATE, pools=pools, deja_utilises=frozenset(), cfg=cfg, rng=rng)

        assert joueur.id == 99999
        assert joueur.club_id is None
        assert joueur.contrat is None
        assert cfg.demographie.generation.age_min <= joueur.date_naissance.age_a(DATE) <= cfg.demographie.generation.age_max
        assert joueur.forme == cfg.etats.forme.initiale
        assert joueur.fatigue == cfg.etats.fatigue.initiale
        assert joueur.moral == cfg.etats.moral.initial
        assert cfg.etats.blessures.fragilite_min <= joueur.fragilite <= cfg.etats.blessures.fragilite_max
        for nom in ("passe", "technique", "finition", "tacle", "jeu_tete", "vision", "placement", "sang_froid", "vitesse", "endurance", "reflexes", "sorties", "relance"):
            valeur = getattr(joueur.attributs, nom)
            assert cfg.attributs.bornes.min <= valeur <= cfg.attributs.bornes.max

    def test_nom_prenom_viennent_du_pool(self, cfg: Config) -> None:
        pools = _pools(cfg)
        joueur = generer_regen(id=1, club_id=None, date_actuelle=DATE, pools=pools, deja_utilises=frozenset(), cfg=cfg, rng=Random(1))
        toutes_les_paires = {paire for paires in pools.par_nation.values() for paire in paires} | {
            (nom, prenom) for _, nom, prenom in pools.exterieur
        }
        assert (joueur.nom, joueur.prenom) in toutes_les_paires


class TestPromouvoirCentreFormation:
    def test_produit_entre_promus_min_et_max(self, cfg: Config) -> None:
        cfg_cf = cfg.demographie.centres_formation
        club = un_club()
        pools = _pools(cfg)

        promus = promouvoir_centre_formation(club, 100000, DATE, pools, frozenset(), cfg, Random(1))
        assert cfg_cf.promus_min <= len(promus) <= cfg_cf.promus_max

    def test_promus_signent_le_bon_contrat(self, cfg: Config) -> None:
        cfg_cf = cfg.demographie.centres_formation
        club = un_club()
        pools = _pools(cfg)

        promus = promouvoir_centre_formation(club, 100000, DATE, pools, frozenset(), cfg, Random(1))
        for joueur in promus:
            assert joueur.club_id == club.id
            assert joueur.contrat is not None
            assert joueur.contrat.salaire_hebdo == round(cfg_cf.salaire_hebdo_base)
            assert joueur.contrat.date_fin == Date(DATE.annee + cfg_cf.duree_contrat_annees, DATE.mois, DATE.jour)

    def test_promus_ont_des_identites_distinctes(self, cfg: Config) -> None:
        club = un_club()
        pools = _pools(cfg)
        promus = promouvoir_centre_formation(club, 100000, DATE, pools, frozenset(), cfg, Random(1))
        paires = [(joueur.nom, joueur.prenom) for joueur in promus]
        assert len(paires) == len(set(paires))
