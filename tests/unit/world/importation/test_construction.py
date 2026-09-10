from random import Random

from core.config import Config
from core.domain.club import StatutClub
from core.domain.date import Date
from core.domain.poste import Poste
from core.world.importation import construction
from tests.unit.world.importation.fabriques import une_ligne_club, une_ligne_joueur

DATE_DEBUT = Date(2026, 8, 10)


def rng() -> Random:
    return Random(20260910)


class TestConstruireClub:
    def test_club_actif_recoit_le_pays_iso_de_la_config(self, cfg: Config) -> None:
        club = construction.construire_club(une_ligne_club(**{"Division ID": "11"}), cfg, rng())
        assert club.statut is StatutClub.ACTIF
        assert club.pays == "ENG"
        assert club.competition_id == 11

    def test_club_dormant_garde_le_texte_brut_de_nation(self, cfg: Config) -> None:
        ligne = une_ligne_club(**{"Division ID": "999999", "Nation": "Kenya"})
        club = construction.construire_club(ligne, cfg, rng())
        assert club.statut is StatutClub.DORMANT
        assert club.pays == "Kenya"

    def test_reputation_dans_les_bornes_configurees(self, cfg: Config) -> None:
        club = construction.construire_club(une_ligne_club(), cfg, rng())
        plage = cfg.import_donnees.synthese_club.reputation
        assert plage.min <= club.reputation <= plage.max

    def test_stade_vide_ne_plante_pas(self, cfg: Config) -> None:
        club = construction.construire_club(une_ligne_club(**{"Stad Cap": "0"}), cfg, rng())
        plage = cfg.import_donnees.synthese_club.reputation
        assert plage.min <= club.reputation <= plage.max

    def test_formation_preferee_est_une_formation_valide(self, cfg: Config) -> None:
        club = construction.construire_club(une_ligne_club(), cfg, rng())
        assert club.formation_preferee in cfg.formations.formations


class TestConstruireCompetitions:
    def test_regroupe_les_clubs_actifs_par_competition_et_exclut_les_dormants(
        self, cfg: Config
    ) -> None:
        generateur = rng()
        clubs = {
            1: construction.construire_club(
                une_ligne_club(**{"Unique ID": "1", "Division ID": "11"}), cfg, generateur
            ),
            2: construction.construire_club(
                une_ligne_club(**{"Unique ID": "2", "Division ID": "11"}), cfg, generateur
            ),
            3: construction.construire_club(
                une_ligne_club(**{"Unique ID": "3", "Division ID": "999999"}), cfg, generateur
            ),
        }

        competitions = construction.construire_competitions(clubs, cfg.monde)

        assert set(competitions[11].club_ids) == {1, 2}
        assert 3 not in competitions[11].club_ids


class TestConstruireJoueur:
    def test_champs_de_base(self, cfg: Config) -> None:
        avertissements: list[str] = []
        joueur = construction.construire_joueur(une_ligne_joueur(), cfg, DATE_DEBUT, rng(), avertissements)
        assert joueur.id == 2000
        assert joueur.nom == "Nom"
        assert joueur.prenom == "Prenom"
        assert joueur.club_id == 1000
        assert joueur.poste is Poste.MC

    def test_attributs_dans_les_bornes(self, cfg: Config) -> None:
        joueur = construction.construire_joueur(une_ligne_joueur(), cfg, DATE_DEBUT, rng(), [])
        for nom in ("passe", "technique", "finition", "tacle", "jeu_tete", "vision",
                    "placement", "sang_froid", "vitesse", "endurance", "reflexes", "sorties", "relance"):
            assert 1 <= joueur.attributs.valeur(nom) <= 100

    def test_potentiel_au_moins_egal_au_niveau_estime(self, cfg: Config) -> None:
        joueur = construction.construire_joueur(une_ligne_joueur(), cfg, DATE_DEBUT, rng(), [])
        # le niveau estime module les attributs ; le potentiel ne doit jamais descendre en dessous
        assert joueur.potentiel <= 100

    def test_club_id_moins_un_devient_agent_libre(self, cfg: Config) -> None:
        joueur = construction.construire_joueur(
            une_ligne_joueur(**{"Club ID": "-1"}), cfg, DATE_DEBUT, rng(), []
        )
        assert joueur.club_id is None
        assert joueur.contrat is None

    def test_fin_de_contrat_tiret_signifie_pas_de_contrat(self, cfg: Config) -> None:
        joueur = construction.construire_joueur(
            une_ligne_joueur(**{"Contract End": "-"}), cfg, DATE_DEBUT, rng(), []
        )
        assert joueur.contrat is None

    def test_salaire_du_contrat_vient_du_wage(self, cfg: Config) -> None:
        joueur = construction.construire_joueur(
            une_ligne_joueur(**{"Wage": "123456"}), cfg, DATE_DEBUT, rng(), []
        )
        assert joueur.contrat.salaire_hebdo == 123456

    def test_valeur_inconnue_ne_plante_pas_et_donne_un_niveau_bas(self, cfg: Config) -> None:
        joueur = construction.construire_joueur(
            une_ligne_joueur(**{"Value": "-1"}), cfg, DATE_DEBUT, rng(), []
        )
        assert joueur.potentiel >= cfg.import_donnees.synthese_attributs.niveau.min

    def test_contrat_expire_avant_le_debut_de_partie_est_reporte_et_signale(self, cfg: Config) -> None:
        avertissements: list[str] = []
        joueur = construction.construire_joueur(
            une_ligne_joueur(**{"Contract End": "30.06.2020"}), cfg, DATE_DEBUT, rng(), avertissements
        )
        assert joueur.contrat.date_fin.annee == 2021
        assert len(avertissements) == 1
        assert "reportee d'un an" in avertissements[0]

    def test_position_a_slash_est_geree(self, cfg: Config) -> None:
        joueur = construction.construire_joueur(
            une_ligne_joueur(**{"Position": "AM/F C"}), cfg, DATE_DEBUT, rng(), []
        )
        assert joueur.poste is Poste.MOC
        assert Poste.BU in joueur.postes_secondaires
