from core.config import Config
from core.domain.date import Date
from core.world.demographie.sorties import probabilite_retraite, sort_du_perimetre
from tests.unit.world.fabriques_domaine import des_attributs, un_joueur

DATE = Date(2026, 8, 10)


class TestProbabiliteRetraite:
    def test_nulle_sous_l_age_minimal(self, cfg: Config) -> None:
        age_minimal = cfg.demographie.sorties.retraite.age_minimal
        jeune = un_joueur(date_naissance=Date(DATE.annee - (age_minimal - 1), 1, 1))
        assert probabilite_retraite(jeune, DATE, cfg) == 0.0

    def test_croit_avec_l_age(self, cfg: Config) -> None:
        age_minimal = cfg.demographie.sorties.retraite.age_minimal
        moins_vieux = un_joueur(id=1, date_naissance=Date(DATE.annee - (age_minimal + 1), 1, 1))
        plus_vieux = un_joueur(id=2, date_naissance=Date(DATE.annee - (age_minimal + 5), 1, 1))
        assert probabilite_retraite(plus_vieux, DATE, cfg) > probabilite_retraite(moins_vieux, DATE, cfg)

    def test_joueur_faible_raccroche_plus_facilement(self, cfg: Config) -> None:
        age_minimal = cfg.demographie.sorties.retraite.age_minimal
        naissance = Date(DATE.annee - (age_minimal + 3), 1, 1)
        faible = un_joueur(id=1, date_naissance=naissance, attributs=des_attributs(**{c: 30 for c in des_attributs().__dataclass_fields__}))
        fort = un_joueur(id=2, date_naissance=naissance, attributs=des_attributs(**{c: 90 for c in des_attributs().__dataclass_fields__}))
        assert probabilite_retraite(faible, DATE, cfg) > probabilite_retraite(fort, DATE, cfg)


class TestSortDuPerimetre:
    def test_faux_si_le_joueur_a_un_club(self, cfg: Config) -> None:
        age_minimal = cfg.demographie.sorties.sortie_perimetre.age_minimal
        joueur = un_joueur(
            date_naissance=Date(DATE.annee - (age_minimal + 5), 1, 1),
            club_id=1,
            potentiel=30,
            attributs=des_attributs(**{c: 20 for c in des_attributs().__dataclass_fields__}),
        )
        assert sort_du_perimetre(joueur, DATE, cfg) is False

    def test_faux_si_trop_jeune(self, cfg: Config) -> None:
        age_minimal = cfg.demographie.sorties.sortie_perimetre.age_minimal
        joueur = un_joueur(
            date_naissance=Date(DATE.annee - (age_minimal - 1), 1, 1),
            club_id=None,
            potentiel=30,
            attributs=des_attributs(**{c: 20 for c in des_attributs().__dataclass_fields__}),
        )
        assert sort_du_perimetre(joueur, DATE, cfg) is False

    def test_vrai_pour_un_joueur_faible_sans_club(self, cfg: Config) -> None:
        age_minimal = cfg.demographie.sorties.sortie_perimetre.age_minimal
        joueur = un_joueur(
            date_naissance=Date(DATE.annee - (age_minimal + 5), 1, 1),
            club_id=None,
            potentiel=30,
            attributs=des_attributs(**{c: 20 for c in des_attributs().__dataclass_fields__}),
        )
        assert sort_du_perimetre(joueur, DATE, cfg) is True

    def test_faux_pour_un_joueur_prometteur_sans_club(self, cfg: Config) -> None:
        age_minimal = cfg.demographie.sorties.sortie_perimetre.age_minimal
        joueur = un_joueur(
            date_naissance=Date(DATE.annee - (age_minimal + 5), 1, 1),
            club_id=None,
            potentiel=90,
            attributs=des_attributs(**{c: 80 for c in des_attributs().__dataclass_fields__}),
        )
        assert sort_du_perimetre(joueur, DATE, cfg) is False
