from core.domain.date import Date
from core.domain.historique import Historique, TransfertHistorique
from core.domain.match import Evenement, Match, ResultatMatch, StatsEquipe, TypeEvenement
from core.world.historique_joueur import _club_a_la_date, historique_saisons
from tests.unit.world.fabriques_domaine import un_club, un_joueur, un_monde

JOUEUR_ID = 1


def _match(id_, saison, date, domicile_id, exterieur_id, notes, buteurs=()):
    evenements = [
        Evenement(minute=1, type=TypeEvenement.BUT, joueur_id=b, joueur_secondaire_id=None, zone=None, couloir=None)
        for b in buteurs
    ]
    resultat = ResultatMatch(
        buts_dom=len(buteurs), buts_ext=0, evenements=evenements, stats_dom=StatsEquipe(), stats_ext=StatsEquipe(),
        notes=notes,
    )
    return Match(id=id_, competition_id=1, journee=1, date=date, domicile_id=domicile_id, exterieur_id=exterieur_id, resultat=resultat, saison=saison)


class TestClubALaDate:
    def test_avant_le_premier_transfert(self) -> None:
        transferts = [TransfertHistorique(date=Date(2027, 1, 1), joueur_id=JOUEUR_ID, club_source_id=10, club_cible_id=20, montant=1)]
        assert _club_a_la_date(club_actuel=20, transferts_joueur=transferts, date=Date(2026, 8, 1)) == 10

    def test_apres_le_dernier_transfert(self) -> None:
        transferts = [TransfertHistorique(date=Date(2027, 1, 1), joueur_id=JOUEUR_ID, club_source_id=10, club_cible_id=20, montant=1)]
        assert _club_a_la_date(club_actuel=20, transferts_joueur=transferts, date=Date(2027, 6, 1)) == 20

    def test_entre_deux_transferts(self) -> None:
        transferts = [
            TransfertHistorique(date=Date(2027, 1, 1), joueur_id=JOUEUR_ID, club_source_id=10, club_cible_id=20, montant=1),
            TransfertHistorique(date=Date(2028, 1, 1), joueur_id=JOUEUR_ID, club_source_id=20, club_cible_id=30, montant=1),
        ]
        assert _club_a_la_date(club_actuel=30, transferts_joueur=transferts, date=Date(2027, 6, 1)) == 20

    def test_sans_aucun_transfert(self) -> None:
        assert _club_a_la_date(club_actuel=10, transferts_joueur=[], date=Date(2020, 1, 1)) == 10


class TestHistoriqueSaisons:
    def test_joueur_sans_match_renvoie_liste_vide(self) -> None:
        joueur = un_joueur(id=JOUEUR_ID, club_id=1)
        monde = un_monde(joueurs={joueur.id: joueur}, clubs={1: un_club(id=1)})
        assert historique_saisons(JOUEUR_ID, monde) == []

    def test_une_saison_un_club_sans_transfert(self) -> None:
        joueur = un_joueur(id=JOUEUR_ID, club_id=1)
        club = un_club(id=1, nom="Club A")
        matches = {
            1: _match(1, 1, Date(2026, 8, 15), 1, 2, {JOUEUR_ID: 7.0}, buteurs=[JOUEUR_ID]),
            2: _match(2, 1, Date(2026, 8, 22), 2, 1, {JOUEUR_ID: 6.0}),
        }
        monde = un_monde(joueurs={joueur.id: joueur}, clubs={1: club, 2: un_club(id=2)}, matches=matches)

        lignes = historique_saisons(JOUEUR_ID, monde)

        assert len(lignes) == 1
        ligne = lignes[0]
        assert ligne.saison == 1
        assert ligne.club_id == 1
        assert ligne.matches_joues == 2
        assert ligne.buts == 1
        assert ligne.note_moyenne == 6.5
        assert ligne.prix_transfert is None

    def test_transfert_en_cours_de_saison_separe_les_deux_clubs(self) -> None:
        joueur = un_joueur(id=JOUEUR_ID, club_id=2)  # club actuel : le club d'arrivee
        transfert = TransfertHistorique(date=Date(2027, 1, 15), joueur_id=JOUEUR_ID, club_source_id=1, club_cible_id=2, montant=5_000_000, saison=1)
        matches = {
            1: _match(1, 1, Date(2026, 9, 1), 1, 3, {JOUEUR_ID: 7.0}, buteurs=[JOUEUR_ID]),  # avant le transfert : club 1
            2: _match(2, 1, Date(2027, 2, 1), 2, 3, {JOUEUR_ID: 8.0}),  # apres le transfert : club 2
        }
        monde = un_monde(
            joueurs={joueur.id: joueur}, clubs={1: un_club(id=1, nom="Ancien"), 2: un_club(id=2, nom="Nouveau"), 3: un_club(id=3)},
            matches=matches, historique=Historique(transferts=[transfert]),
        )

        lignes = historique_saisons(JOUEUR_ID, monde)

        assert len(lignes) == 2
        ancien, nouveau = lignes[0], lignes[1]  # date_min croissante au sein d'une meme saison
        assert ancien.club_id == 1 and ancien.matches_joues == 1 and ancien.buts == 1 and ancien.prix_transfert is None
        assert nouveau.club_id == 2 and nouveau.matches_joues == 1 and nouveau.prix_transfert == 5_000_000

    def test_tri_par_saison_decroissante(self) -> None:
        joueur = un_joueur(id=JOUEUR_ID, club_id=1)
        matches = {
            1: _match(1, 1, Date(2026, 9, 1), 1, 2, {JOUEUR_ID: 6.0}),
            2: _match(2, 2, Date(2027, 9, 1), 1, 2, {JOUEUR_ID: 6.0}),
        }
        monde = un_monde(joueurs={joueur.id: joueur}, clubs={1: un_club(id=1), 2: un_club(id=2)}, matches=matches)

        lignes = historique_saisons(JOUEUR_ID, monde)

        assert [l.saison for l in lignes] == [2, 1]
