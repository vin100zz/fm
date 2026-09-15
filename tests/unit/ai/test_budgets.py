import pytest

from core.ai.budgets import (
    calculer_budget_transfert,
    calculer_masse_salariale_max,
    calculer_revenus,
    depense_mensuelle_salaires,
    masse_salariale_max_reelle,
    prime_classement,
    revenu_mensuel,
)
from core.config import Config
from tests.unit.world.fabriques_domaine import un_joueur


def test_revenus_croissent_avec_la_reputation(cfg: Config) -> None:
    faible = calculer_revenus(20, "FRA", None, cfg)
    fort = calculer_revenus(90, "FRA", None, cfg)
    assert fort > faible


def test_revenus_varient_selon_le_pays(cfg: Config) -> None:
    angleterre = calculer_revenus(60, "ENG", None, cfg)
    france = calculer_revenus(60, "FRA", None, cfg)
    assert angleterre > france  # multiplicateur_pays["ENG"] > multiplicateur_pays["FRA"] en config


def test_revenus_bonus_pour_le_champion_sortant(cfg: Config) -> None:
    sans_classement = calculer_revenus(60, "FRA", None, cfg)
    champion = calculer_revenus(60, "FRA", 1, cfg)
    assert champion > sans_classement


def test_budget_transfert_combine_revenus_solde_et_ventes(cfg: Config) -> None:
    cfg_b = cfg.ia.budgets
    budget = calculer_budget_transfert(revenus_saison=10_000_000, solde=1_000_000, ventes_realisees=500_000, cfg=cfg)
    attendu = round(10_000_000 * cfg_b.part_revenus_transfert + 1_000_000 * cfg_b.part_solde_transfert + 500_000)
    assert budget == attendu


def test_masse_salariale_max_est_hebdomadaire(cfg: Config) -> None:
    cfg_b = cfg.ia.budgets
    masse = calculer_masse_salariale_max(revenus_saison=52_000_000, cfg=cfg)
    assert masse == round(52_000_000 * cfg_b.part_revenus_salaires / cfg_b.semaines_par_an)


def test_prime_classement_decroit_avec_la_place(cfg: Config) -> None:
    cfg_rev = cfg.ia.budgets.revenus
    assert prime_classement(1, cfg) == round(cfg_rev.bonus_classement_premier)
    assert prime_classement(2, cfg) < prime_classement(1, cfg)
    assert prime_classement(2, cfg) == round(cfg_rev.bonus_classement_premier * cfg_rev.decroissance_par_place)


def test_revenu_mensuel_ajoute_une_marge_fixe_a_la_masse_salariale_reelle(cfg: Config) -> None:
    cfg_b = cfg.ia.budgets
    mensuel = revenu_mensuel(masse_salariale_hebdo=1_000_000, cfg=cfg)
    salaire_mensuel = 1_000_000 * cfg_b.semaines_par_an / 12
    assert mensuel == round(salaire_mensuel * (1 + cfg_b.marge_revenu_mensuel))
    assert mensuel > salaire_mensuel


def test_revenu_mensuel_croit_avec_la_masse_salariale_reelle(cfg: Config) -> None:
    assert revenu_mensuel(2_000_000, cfg) > revenu_mensuel(1_000_000, cfg)


def test_depense_mensuelle_salaires_annualise_le_salaire_hebdomadaire(cfg: Config) -> None:
    cfg_b = cfg.ia.budgets
    effectif = [un_joueur(id=1), un_joueur(id=2)]
    masse_hebdo = sum(j.contrat.salaire_hebdo for j in effectif)

    depense = depense_mensuelle_salaires(effectif, cfg)

    assert depense == round(masse_hebdo * cfg_b.semaines_par_an / 12)


def test_depense_mensuelle_salaires_ignore_les_joueurs_sans_contrat(cfg: Config) -> None:
    effectif = [un_joueur(id=1, contrat=None)]
    assert depense_mensuelle_salaires(effectif, cfg) == 0


def test_masse_salariale_max_reelle_suit_la_masse_salariale_importee_si_plus_genereuse(cfg: Config) -> None:
    cfg_b = cfg.ia.budgets
    plafond = masse_salariale_max_reelle(masse_salariale_importee=10_000_000, plafond_reputation=1_000_000, cfg=cfg)
    assert plafond == round(10_000_000 * (1 + cfg_b.marge_masse_salariale_initiale))


def test_masse_salariale_max_reelle_garde_le_plafond_de_reputation_comme_plancher(cfg: Config) -> None:
    # Effectif sans donnees de contrat (masse salariale importee nulle) :
    # le plafond derive de la reputation sert de plancher plutot que de
    # laisser le club bloque a ~0.
    plafond = masse_salariale_max_reelle(masse_salariale_importee=0, plafond_reputation=1_000_000, cfg=cfg)
    assert plafond == 1_000_000
