from random import Random

from core.config import Config
from core.domain.date import Date
from core.domain.etat_joueur import Suspension
from core.domain.journal import TypeEvenementJour
from core.domain.poste import Poste
from core.world.saison import avancer_jusqua_journee, avancer_un_jour, initialiser_saison, matches_saison_courante
from tests.unit.world.fabriques_domaine import un_club, un_effectif_complet, un_joueur, un_monde, une_competition


def _petit_monde() -> tuple:
    clubs = {i: un_club(id=i, nom=f"Club{i}", nom_court=f"C{i}", competition_id=1) for i in range(1, 5)}
    joueurs = {}
    for club_id in clubs:
        for joueur in un_effectif_complet(club_id):
            joueur.id += club_id * 10_000  # ids uniques : un_effectif_complet() se recoupe sinon entre clubs
            joueurs[joueur.id] = joueur
    competition = une_competition(id=1, club_ids=list(clubs.keys()))
    monde = un_monde(clubs=clubs, joueurs=joueurs, competitions={1: competition})
    return monde, competition


def test_initialiser_saison_est_idempotente(cfg: Config) -> None:
    monde, competition = _petit_monde()
    rng = Random(1)

    initialiser_saison(monde, cfg, rng)
    nb_matches_apres_premier_appel = len(monde.matches)
    initialiser_saison(monde, cfg, rng)

    assert len(monde.matches) == nb_matches_apres_premier_appel
    assert nb_matches_apres_premier_appel == 4 * 3  # 4 clubs, aller-retour


def test_avancer_un_jour_avance_la_date(cfg: Config) -> None:
    monde, _ = _petit_monde()
    initialiser_saison(monde, cfg, Random(1))
    date_avant = monde.date

    avancer_un_jour(monde, cfg, Random(1))

    assert monde.date.jours_jusqua(date_avant) == -1


def test_avancer_un_jour_joue_les_matches_programmes_ce_jour(cfg: Config) -> None:
    monde, competition = _petit_monde()
    initialiser_saison(monde, cfg, Random(1))
    premiere_journee = competition.calendrier[0]
    ids_du_jour = list(premiere_journee.match_ids)

    journal = avancer_un_jour(monde, cfg, Random(1))

    for match_id in ids_du_jour:
        assert monde.matches[match_id].resultat is not None
    assert any(e.type is TypeEvenementJour.RESULTAT for e in journal)


def test_avancer_un_jour_recupere_la_fatigue_un_jour_sans_match(cfg: Config) -> None:
    monde, _ = _petit_monde()
    initialiser_saison(monde, cfg, Random(1))
    avancer_un_jour(monde, cfg, Random(1))  # joue la 1ere journee

    un_joueur_quelconque = next(iter(monde.joueurs.values()))
    un_joueur_quelconque.fatigue = 0.5

    # jours_entre_journees vaut 7 en config : le jour suivant n'a aucun match programme.
    avancer_un_jour(monde, cfg, Random(1))

    assert un_joueur_quelconque.fatigue > 0.5


def test_avancer_un_jour_decremente_les_suspensions_du_club_qui_joue(cfg: Config) -> None:
    monde, competition = _petit_monde()
    initialiser_saison(monde, cfg, Random(1))
    premier_match = monde.matches[competition.calendrier[0].match_ids[0]]
    joueur_du_club = next(j for j in monde.joueurs.values() if j.club_id == premier_match.domicile_id)
    joueur_du_club.suspension = Suspension(matches_restants=2, motif="test")

    avancer_un_jour(monde, cfg, Random(1))

    assert joueur_du_club.suspension.matches_restants == 1


def test_avancer_jusqua_journee_retourne_des_resultats(cfg: Config) -> None:
    monde, _ = _petit_monde()
    initialiser_saison(monde, cfg, Random(1))

    journal = avancer_jusqua_journee(monde, cfg, Random(1))

    assert any(e.type is TypeEvenementJour.RESULTAT for e in journal)


def _jouer_toute_la_saison(monde, cfg: Config, rng: Random, competition, limite_jours: int = 90) -> None:
    """Joue jusqu'à ce que tous les matchs de la saison en cours de
    `competition` aient un résultat — mais, depuis que la saison ne
    bascule plus qu'au 1er juillet (voir `_relancer_saison_au_1er_juillet`),
    ça ne déclenche plus rien tout seul : le calendrier reste simplement
    épuisé jusqu'à la prochaine bascule.
    """
    for _ in range(limite_jours):
        avancer_un_jour(monde, cfg, rng)
        matches = matches_saison_courante(competition, monde)
        if matches and all(m.resultat is not None for m in matches):
            return
    raise AssertionError("saison non terminee dans la limite de jours")


def _sauter_au_1er_juillet_suivant(monde, cfg: Config, rng: Random) -> list:
    """Place `monde.date` la veille du prochain 1er juillet (celui de
    l'an prochain si on l'a déjà dépassé cette année) puis avance d'un
    jour, pour déclencher `_relancer_saison_au_1er_juillet` sans avoir à
    boucler jour par jour sur tout le creux estival (~100 jours).
    """
    annee = monde.date.annee if monde.date < Date(monde.date.annee, 7, 1) else monde.date.annee + 1
    monde.date = Date(annee, 6, 30)
    return avancer_un_jour(monde, cfg, rng)


class TestFinDeSaison:
    def test_relance_une_nouvelle_saison_le_1er_juillet(self, cfg: Config) -> None:
        monde, competition = _petit_monde()
        initialiser_saison(monde, cfg, Random(1))
        rng = Random(1)
        _jouer_toute_la_saison(monde, cfg, rng, competition)

        journal = _sauter_au_1er_juillet_suivant(monde, cfg, rng)

        assert monde.date == Date(monde.date.annee, 7, 1)
        fins = [e for e in journal if e.type is TypeEvenementJour.FIN_DE_SAISON]
        assert len(fins) == 1
        assert fins[0].competition_id == competition.id
        assert competition.saison_actuelle == 2
        assert monde.saison == 2

    def test_ne_bascule_pas_avant_le_1er_juillet_meme_calendrier_epuise(self, cfg: Config) -> None:
        monde, competition = _petit_monde()
        initialiser_saison(monde, cfg, Random(1))
        rng = Random(1)

        _jouer_toute_la_saison(monde, cfg, rng, competition)

        assert competition.saison_actuelle == 1
        assert monde.historique.palmares == []
        assert monde.date.mois != 7 or monde.date.jour != 1

    def test_archive_le_classement_final_dans_le_palmares(self, cfg: Config) -> None:
        monde, competition = _petit_monde()
        initialiser_saison(monde, cfg, Random(1))
        rng = Random(1)
        _jouer_toute_la_saison(monde, cfg, rng, competition)

        _sauter_au_1er_juillet_suivant(monde, cfg, rng)

        assert len(monde.historique.palmares) == 1
        saison_archivee = monde.historique.palmares[0]
        assert saison_archivee.saison == 1
        assert saison_archivee.competition_id == competition.id
        assert {ligne.club_id for ligne in saison_archivee.classement_final} == set(competition.club_ids)
        assert saison_archivee.champion_id == saison_archivee.classement_final[0].club_id

    def test_genere_un_nouveau_calendrier_pour_les_memes_clubs_a_partir_d_aout(self, cfg: Config) -> None:
        monde, competition = _petit_monde()
        initialiser_saison(monde, cfg, Random(1))
        rng = Random(1)
        _jouer_toute_la_saison(monde, cfg, rng, competition)

        _sauter_au_1er_juillet_suivant(monde, cfg, rng)

        nouveaux_matches = matches_saison_courante(competition, monde)
        assert len(nouveaux_matches) == 4 * 3  # 4 clubs, aller-retour — memes club_ids, pas de promotion/relegation
        assert all(m.resultat is None for m in nouveaux_matches)
        assert all(m.saison == 2 for m in nouveaux_matches)
        premier_match = min(nouveaux_matches, key=lambda m: m.date)
        assert (premier_match.date.mois, premier_match.date.jour) == (cfg.monde.saison.debut_mois, cfg.monde.saison.debut_jour)
        assert {c.id for c in monde.clubs.values() if c.id in competition.club_ids} == set(competition.club_ids)

    def test_reinitialise_le_cumul_de_cartons_jaunes(self, cfg: Config) -> None:
        monde, competition = _petit_monde()
        initialiser_saison(monde, cfg, Random(1))
        joueur = next(j for j in monde.joueurs.values() if j.club_id in competition.club_ids)
        joueur.cartons_jaunes_saison = 4
        rng = Random(1)
        _jouer_toute_la_saison(monde, cfg, rng, competition)

        _sauter_au_1er_juillet_suivant(monde, cfg, rng)

        assert joueur.cartons_jaunes_saison == 0


def test_blessures_hors_match_surviennent_sur_une_grande_population(cfg: Config) -> None:
    # config reel : probabilite_quotidienne_hors_match tres faible (0.00035) —
    # une population et un nombre de jours assez grands pour la rendre quasi certaine.
    joueurs = {}
    club = un_club(id=1)
    for i in range(500):
        joueurs[i] = un_joueur(id=i, club_id=1, poste=Poste.MC)
    monde = un_monde(clubs={1: club}, joueurs=joueurs, competitions={})

    rng = Random(1)
    blesses = 0
    for _ in range(20):
        avancer_un_jour(monde, cfg, rng)
        blesses = sum(1 for j in joueurs.values() if j.blessure is not None)
        if blesses:
            break

    assert blesses > 0
