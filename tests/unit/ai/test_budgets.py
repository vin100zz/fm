from core.ai.budgets import calculer_budget_transfert, calculer_masse_salariale_max, calculer_revenus
from core.config import Config


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
