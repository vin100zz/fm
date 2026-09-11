from core.config import Config
from core.domain.date import Date
from core.world.etats.fatigue import consommer, recuperer
from tests.unit.world.fabriques_domaine import des_attributs, un_joueur

DATE = Date(2026, 8, 10)


class TestConsommer:
    def test_reduit_la_fatigue(self, cfg: Config) -> None:
        joueur = un_joueur(fatigue=1.0)
        consommer(joueur, minutes=90, intensite=1.0, cfg=cfg.etats.fatigue)
        assert joueur.fatigue < 1.0

    def test_ne_descend_jamais_sous_le_minimum(self, cfg: Config) -> None:
        joueur = un_joueur(fatigue=0.01)
        consommer(joueur, minutes=90, intensite=1.20, cfg=cfg.etats.fatigue)
        assert joueur.fatigue >= cfg.etats.fatigue.min

    def test_endurance_plus_haute_epuise_moins(self, cfg: Config) -> None:
        endurant = un_joueur(id=1, fatigue=1.0, attributs=des_attributs(endurance=95))
        fragile = un_joueur(id=2, fatigue=1.0, attributs=des_attributs(endurance=20))

        consommer(endurant, minutes=90, intensite=1.0, cfg=cfg.etats.fatigue)
        consommer(fragile, minutes=90, intensite=1.0, cfg=cfg.etats.fatigue)

        assert endurant.fatigue > fragile.fatigue

    def test_pressing_haut_fatigue_plus_que_bloc_bas(self, cfg: Config) -> None:
        cfg_fatigue = cfg.etats.fatigue
        presseur = un_joueur(id=1, fatigue=1.0)
        passif = un_joueur(id=2, fatigue=1.0)

        consommer(presseur, 90, cfg_fatigue.intensite_par_hauteur_bloc.pressing_haut, cfg_fatigue)
        consommer(passif, 90, cfg_fatigue.intensite_par_hauteur_bloc.bloc_bas, cfg_fatigue)

        assert presseur.fatigue < passif.fatigue


class TestRecuperer:
    def test_augmente_la_fatigue_vers_le_maximum(self, cfg: Config) -> None:
        joueur = un_joueur(fatigue=0.5, date_naissance=Date(1995, 1, 1))
        recuperer(joueur, jours=3, date_actuelle=DATE, cfg=cfg.etats.fatigue)
        assert joueur.fatigue > 0.5

    def test_ne_depasse_jamais_le_maximum(self, cfg: Config) -> None:
        joueur = un_joueur(fatigue=0.99, date_naissance=Date(1995, 1, 1))
        recuperer(joueur, jours=30, date_actuelle=DATE, cfg=cfg.etats.fatigue)
        assert joueur.fatigue <= cfg.etats.fatigue.max

    def test_jeune_recupere_plus_vite(self, cfg: Config) -> None:
        cfg_fatigue = cfg.etats.fatigue
        jeune = un_joueur(id=1, fatigue=0.5, date_naissance=Date(DATE.annee - (cfg_fatigue.seuil_age_jeune - 1), 1, 1))
        vieux = un_joueur(id=2, fatigue=0.5, date_naissance=Date(DATE.annee - (cfg_fatigue.seuil_age_vieux + 5), 1, 1))

        recuperer(jeune, jours=1, date_actuelle=DATE, cfg=cfg_fatigue)
        recuperer(vieux, jours=1, date_actuelle=DATE, cfg=cfg_fatigue)

        assert jeune.fatigue > vieux.fatigue
