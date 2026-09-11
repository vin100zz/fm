from random import Random

from core.config import Config
from core.domain.date import Date
from core.world.note_globale import note_globale
from core.world.progression import facteur_par_age, progresser
from tests.unit.world.fabriques_domaine import des_attributs, un_joueur

DATE_ACTUELLE = Date(2026, 8, 10)


class TestFacteurParAge:
    def test_au_milieu_dun_palier_retourne_son_facteur(self, cfg: Config) -> None:
        paliers = cfg.demographie.progression.courbe_age
        milieu_premier = (paliers[0].age_min + paliers[0].age_max) / 2
        assert facteur_par_age(milieu_premier, paliers) == paliers[0].facteur

    def test_avant_le_premier_palier_est_borne(self, cfg: Config) -> None:
        paliers = cfg.demographie.progression.courbe_age
        assert facteur_par_age(0, paliers) == paliers[0].facteur

    def test_apres_le_dernier_palier_est_borne(self, cfg: Config) -> None:
        paliers = cfg.demographie.progression.courbe_age
        assert facteur_par_age(200, paliers) == paliers[-1].facteur

    def test_interpole_entre_deux_milieux(self, cfg: Config) -> None:
        paliers = cfg.demographie.progression.courbe_age
        milieu_a = (paliers[0].age_min + paliers[0].age_max) / 2
        milieu_b = (paliers[1].age_min + paliers[1].age_max) / 2
        valeur_milieu = facteur_par_age((milieu_a + milieu_b) / 2, paliers)
        borne_basse, borne_haute = sorted((paliers[0].facteur, paliers[1].facteur))
        assert borne_basse <= valeur_milieu <= borne_haute


class TestProgresser:
    def test_jeune_joueur_avec_marge_progresse(self, cfg: Config) -> None:
        joueur = un_joueur(
            date_naissance=Date(2008, 1, 1),  # ~18 ans, courbe_age favorable
            attributs=des_attributs(),  # tout a 50
            potentiel=90,  # grosse marge
        )
        niveau_avant = note_globale(joueur, cfg.attributs)

        progresser(joueur, minutes_mois=400, date_actuelle=DATE_ACTUELLE, rng=Random(1), cfg=cfg)

        assert note_globale(joueur, cfg.attributs) > niveau_avant

    def test_ne_depasse_jamais_le_potentiel(self, cfg: Config) -> None:
        joueur = un_joueur(
            date_naissance=Date(2008, 1, 1),
            attributs=des_attributs(),
            potentiel=51,  # marge minuscule
        )

        for _ in range(24):  # deux ans de progression mensuelle
            progresser(joueur, minutes_mois=400, date_actuelle=DATE_ACTUELLE, rng=Random(1), cfg=cfg)

        assert note_globale(joueur, cfg.attributs) <= joueur.potentiel + 1e-6

    def test_vieux_joueur_decline(self, cfg: Config) -> None:
        # potentiel au-dessus du niveau actuel : une marge positive est
        # necessaire pour que le terme d'age (negatif a cet age) produise
        # un delta negatif — a marge nulle, seul le bruit s'applique et
        # le declin par age ne se manifeste pas du tout.
        joueur = un_joueur(date_naissance=Date(1988, 1, 1), attributs=des_attributs(), potentiel=70)
        niveau_avant = note_globale(joueur, cfg.attributs)
        rng = Random(1)

        for _ in range(12):
            progresser(joueur, minutes_mois=400, date_actuelle=DATE_ACTUELLE, rng=rng, cfg=cfg)

        assert note_globale(joueur, cfg.attributs) < niveau_avant

    def test_declin_touche_vitesse_plus_que_sang_froid(self, cfg: Config) -> None:
        joueur = un_joueur(date_naissance=Date(1988, 1, 1), attributs=des_attributs(), potentiel=70)
        vitesse_avant, sang_froid_avant = joueur.attributs.vitesse, joueur.attributs.sang_froid
        rng = Random(1)

        for _ in range(12):
            progresser(joueur, minutes_mois=400, date_actuelle=DATE_ACTUELLE, rng=rng, cfg=cfg)

        assert (vitesse_avant - joueur.attributs.vitesse) > (sang_froid_avant - joueur.attributs.sang_froid)

    def test_joueur_qui_ne_joue_pas_progresse_moins(self, cfg: Config) -> None:
        beaucoup = un_joueur(id=1, date_naissance=Date(2008, 1, 1), attributs=des_attributs(), potentiel=95)
        peu = un_joueur(id=2, date_naissance=Date(2008, 1, 1), attributs=des_attributs(), potentiel=95)
        rng_beaucoup, rng_peu = Random(1), Random(1)

        for _ in range(6):
            progresser(beaucoup, minutes_mois=400, date_actuelle=DATE_ACTUELLE, rng=rng_beaucoup, cfg=cfg)
            progresser(peu, minutes_mois=0, date_actuelle=DATE_ACTUELLE, rng=rng_peu, cfg=cfg)

        assert note_globale(beaucoup, cfg.attributs) > note_globale(peu, cfg.attributs)

    def test_attributs_restent_dans_les_bornes(self, cfg: Config) -> None:
        joueur = un_joueur(date_naissance=Date(1985, 1, 1), attributs=des_attributs(vitesse=2), potentiel=50)

        for _ in range(60):
            progresser(joueur, minutes_mois=400, date_actuelle=DATE_ACTUELLE, rng=Random(1), cfg=cfg)

        assert cfg.attributs.bornes.min <= joueur.attributs.vitesse <= cfg.attributs.bornes.max
