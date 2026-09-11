from random import Random

from core.config import Config
from core.domain.date import Date
from core.world.etats.blessures import evaluer_blessure_hors_match, retablir, tirer_blessure
from tests.unit.world.fabriques_domaine import des_attributs, un_joueur

DATE_DEBUT = Date(2026, 8, 10)


class TestTirerBlessure:
    def test_date_fin_est_apres_date_debut(self, cfg: Config) -> None:
        for graine in range(50):
            blessure = tirer_blessure(DATE_DEBUT, cfg.etats.blessures, Random(graine))
            assert blessure.date_fin > blessure.date_debut

    def test_gravite_est_une_des_configurees(self, cfg: Config) -> None:
        noms_valides = {g.nom for g in cfg.etats.blessures.gravites}
        for graine in range(50):
            blessure = tirer_blessure(DATE_DEBUT, cfg.etats.blessures, Random(graine))
            assert blessure.gravite.value in noms_valides


class TestEvaluerBlessureHorsMatch:
    def test_ne_blesse_pas_un_joueur_deja_blesse(self, cfg: Config) -> None:
        joueur = un_joueur()
        joueur.blessure = tirer_blessure(DATE_DEBUT, cfg.etats.blessures, Random(1))
        blessure_avant = joueur.blessure

        evaluer_blessure_hors_match(joueur, DATE_DEBUT, cfg.etats.blessures, Random(1))

        assert joueur.blessure is blessure_avant

    def test_peut_blesser_un_joueur_sain_sur_assez_de_tirages(self, cfg: Config) -> None:
        blesse_au_moins_une_fois = False
        for graine in range(2000):
            joueur = un_joueur()
            if evaluer_blessure_hors_match(joueur, DATE_DEBUT, cfg.etats.blessures, Random(graine)):
                blesse_au_moins_une_fois = True
                break
        assert blesse_au_moins_une_fois


class TestRetablir:
    def test_efface_la_blessure(self, cfg: Config) -> None:
        joueur = un_joueur()
        joueur.blessure = tirer_blessure(DATE_DEBUT, cfg.etats.blessures, Random(1))

        retablir(joueur, cfg, Random(1))

        assert joueur.blessure is None

    def test_reinitialise_fatigue_et_forme(self, cfg: Config) -> None:
        joueur = un_joueur(fatigue=1.0, forme=1.3)
        joueur.blessure = tirer_blessure(DATE_DEBUT, cfg.etats.blessures, Random(1))

        retablir(joueur, cfg, Random(1))

        assert joueur.fatigue == cfg.etats.fatigue.fatigue_retour_de_blessure
        assert joueur.forme == cfg.etats.blessures.forme_retour_de_blessure

    def test_ne_fait_rien_si_pas_blesse(self, cfg: Config) -> None:
        joueur = un_joueur(fatigue=0.7, forme=1.1)
        retablir(joueur, cfg, Random(1))
        assert joueur.fatigue == 0.7
        assert joueur.forme == 1.1

    def test_penalite_permanente_sur_blessure_longue_apres_trente_ans(self, cfg: Config) -> None:
        penalite = cfg.etats.blessures.penalite_permanente
        joueur = un_joueur(
            date_naissance=Date(DATE_DEBUT.annee - penalite.age_minimal - 1, 1, 1),
            attributs=des_attributs(vitesse=80, endurance=80),
        )
        # blessure "tres_grave" forcee : injecter directement plutot que de retirer au hasard
        from core.domain.etat_joueur import Blessure, Gravite

        joueur.blessure = Blessure(
            date_debut=DATE_DEBUT,
            date_fin=DATE_DEBUT.plus_jours(penalite.duree_minimale_jours + 10),
            gravite=Gravite.TRES_GRAVE,
            description="test",
        )

        retablir(joueur, cfg, Random(1))

        assert joueur.attributs.vitesse < 80
        assert joueur.attributs.endurance < 80

    def test_pas_de_penalite_pour_une_blessure_courte(self, cfg: Config) -> None:
        penalite = cfg.etats.blessures.penalite_permanente
        joueur = un_joueur(
            date_naissance=Date(DATE_DEBUT.annee - penalite.age_minimal - 1, 1, 1),
            attributs=des_attributs(vitesse=80, endurance=80),
        )
        from core.domain.etat_joueur import Blessure, Gravite

        joueur.blessure = Blessure(
            date_debut=DATE_DEBUT,
            date_fin=DATE_DEBUT.plus_jours(5),
            gravite=Gravite.LEGERE,
            description="test",
        )

        retablir(joueur, cfg, Random(1))

        assert joueur.attributs.vitesse == 80
        assert joueur.attributs.endurance == 80
