from random import Random

from core.config import Config
from core.domain.etat_joueur import Suspension
from core.world.etats.suspensions import decrementer, enregistrer_jaune, enregistrer_rouge, reinitialiser_saison
from tests.unit.world.fabriques_domaine import un_joueur


class TestDecrementer:
    def test_reduit_le_compte_de_un(self) -> None:
        joueur = un_joueur()
        joueur.suspension = Suspension(matches_restants=3, motif="test")
        decrementer(joueur)
        assert joueur.suspension.matches_restants == 2

    def test_leve_la_suspension_a_zero(self) -> None:
        joueur = un_joueur()
        joueur.suspension = Suspension(matches_restants=1, motif="test")
        decrementer(joueur)
        assert joueur.suspension is None

    def test_ne_plante_pas_sans_suspension(self) -> None:
        joueur = un_joueur()
        decrementer(joueur)
        assert joueur.suspension is None


class TestEnregistrerJaune:
    def test_incremente_le_cumul_de_la_saison(self, cfg: Config) -> None:
        joueur = un_joueur()
        enregistrer_jaune(joueur, cfg.etats.suspensions)
        assert joueur.cartons_jaunes_saison == 1

    def test_declenche_une_suspension_au_seuil(self, cfg: Config) -> None:
        premier_seuil = cfg.etats.suspensions.seuils_cumul_jaunes[0]
        joueur = un_joueur()
        joueur.cartons_jaunes_saison = premier_seuil.jaunes - 1

        enregistrer_jaune(joueur, cfg.etats.suspensions)

        assert joueur.suspension is not None
        assert joueur.suspension.matches_restants == premier_seuil.matches

    def test_ne_declenche_rien_hors_seuil(self, cfg: Config) -> None:
        premier_seuil = cfg.etats.suspensions.seuils_cumul_jaunes[0]
        joueur = un_joueur()
        joueur.cartons_jaunes_saison = premier_seuil.jaunes - 2

        enregistrer_jaune(joueur, cfg.etats.suspensions)

        assert joueur.suspension is None


class TestEnregistrerRouge:
    def test_rouge_directe_tire_dans_la_plage_configuree(self, cfg: Config) -> None:
        cfg_susp = cfg.etats.suspensions
        for graine in range(50):
            joueur = un_joueur()
            enregistrer_rouge(joueur, deuxieme_jaune=False, cfg=cfg_susp, rng=Random(graine))
            assert cfg_susp.matches_rouge_min <= joueur.suspension.matches_restants <= cfg_susp.matches_rouge_max

    def test_deuxieme_jaune_donne_la_duree_fixe_configuree(self, cfg: Config) -> None:
        cfg_susp = cfg.etats.suspensions
        joueur = un_joueur()
        enregistrer_rouge(joueur, deuxieme_jaune=True, cfg=cfg_susp, rng=Random(1))
        assert joueur.suspension.matches_restants == cfg_susp.matches_double_jaune


def test_reinitialiser_saison_remet_le_cumul_a_zero(cfg: Config) -> None:
    joueur = un_joueur()
    joueur.cartons_jaunes_saison = 7
    reinitialiser_saison(joueur, cfg.etats.suspensions)
    assert joueur.cartons_jaunes_saison == 0
