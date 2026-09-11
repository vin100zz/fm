import math
from random import Random

from core.ai.besoins import profondeur_utile
from core.ai.valorisation import valeur
from core.config import Config
from core.config.modeles.monde import FenetreMercato
from core.domain.club import PersonnaliteClub, StatutClub
from core.domain.date import Date
from core.domain.negociation import Negociation
from core.domain.poste import Poste
from core.world.mercato import _dans_fenetre, avancer_mercato, fenetre_mercato_ouverte, tour_mercato
from tests.unit.world.fabriques_domaine import des_attributs, un_club, un_joueur, un_monde


class _RngDemarcheForce:
    """Remplace le `Random` injecte pour forcer le tirage du demarchage
    (`_demarcher_surplus`) a reussir de façon deterministe, plutot que
    de chercher une graine qui tombe bien — meme principe que le
    `RngFixe` de docs/architecture.md."""

    def random(self) -> float:
        return 0.0  # toujours < probabilite_demarchage_par_tour

    def choice(self, sequence):
        return sequence[0]

    def gauss(self, mu: float, sigma: float) -> float:
        return mu

    def uniform(self, a: float, b: float) -> float:
        return a


class _RngDemarcheRefuse(_RngDemarcheForce):
    """Meme principe, dans l'autre sens : garantit que le tirage du
    demarchage echoue toujours, plutot que de compter sur une graine
    reelle dont la probabilite de succes (faible, mais non nulle) rendrait
    le test statistiquement flaky."""

    def random(self) -> float:
        return 0.999999

AUTRES_POSTES = [Poste.GB, Poste.DC, Poste.DC, Poste.DL, Poste.DR, Poste.MOC, Poste.AILG, Poste.AILD, Poste.BU, Poste.BU]


def _uniforme(note: int):
    return des_attributs(**{champ: note for champ in des_attributs().__dataclass_fields__})


def _monde_avec_besoin_mc():
    """Club 1 (acheteur) n'a aucun joueur au poste MC — un besoin MANQUE
    garanti. Le candidat (niveau 85) est nettement au-dessus du niveau
    uniforme du reste de l'effectif (70) : `meilleure_affectation` étant
    gloutonne (pas un assignment optimal), un candidat trop proche du
    niveau existant peut donner une utilité marginale légèrement
    négative malgré le poste vide (vérifié à la main : niveau 68 donne
    -0.18, 75+ devient et reste nettement positif) — 85 est pris pour
    laisser une marge confortable, pas la valeur minimale qui marche.
    Club 2 (vendeur) a un unique MC (donc `surplus() == 0`, aucune
    remise) et une patience de négociation nulle (aucune prime) : le
    seuil vendeur est le cas de base exact,
    `valeur * seuil_vendeur_multiplicateur` — la seule inconnue
    restante, ce qui rend le déroulé de la négociation prévisible pour
    le test.
    """
    club_acheteur = un_club(id=1, reputation=60, budget_transfert=500_000_000, masse_salariale_max=5_000_000)
    club_vendeur = un_club(
        id=2, reputation=60, budget_transfert=10_000_000, masse_salariale_max=1_000_000,
        personnalite=PersonnaliteClub(0.5, 0.5, 0.5, 0.0),
    )

    joueurs = {}
    for i, poste in enumerate(AUTRES_POSTES * 2):  # effectif de taille 20, sans aucun MC
        j = un_joueur(id=1000 + i, poste=poste, club_id=1, attributs=_uniforme(70))
        joueurs[j.id] = j

    cible_id = 2000
    joueurs[cible_id] = un_joueur(id=cible_id, poste=Poste.MC, club_id=2, attributs=_uniforme(85))

    monde = un_monde(date=Date(2026, 8, 10), clubs={1: club_acheteur, 2: club_vendeur}, joueurs=joueurs)
    return monde, cible_id


class TestFenetreMercato:
    def test_fenetre_mercato_ouverte_pendant_l_ete(self, cfg: Config) -> None:
        assert fenetre_mercato_ouverte(Date(2026, 7, 1), cfg) is True

    def test_fenetre_mercato_fermee_hors_saison(self, cfg: Config) -> None:
        assert fenetre_mercato_ouverte(Date(2026, 3, 15), cfg) is False

    def test_avancer_mercato_ne_fait_rien_hors_fenetre(self, cfg: Config) -> None:
        monde, _ = _monde_avec_besoin_mc()
        monde.date = Date(2026, 3, 15)
        assert avancer_mercato(monde, cfg, Random(1)) == []
        assert monde.negociations == []

    def test_dans_fenetre_bornes_incluses(self) -> None:
        fenetre = FenetreMercato(debut_mois=6, debut_jour=10, fin_mois=8, fin_jour=31)
        assert _dans_fenetre(Date(2026, 6, 10), fenetre) is True
        assert _dans_fenetre(Date(2026, 8, 31), fenetre) is True
        assert _dans_fenetre(Date(2026, 6, 9), fenetre) is False
        assert _dans_fenetre(Date(2026, 9, 1), fenetre) is False

    def test_dans_fenetre_a_cheval_sur_le_nouvel_an(self) -> None:
        fenetre = FenetreMercato(debut_mois=12, debut_jour=20, fin_mois=1, fin_jour=10)
        assert _dans_fenetre(Date(2026, 12, 25), fenetre) is True
        assert _dans_fenetre(Date(2027, 1, 5), fenetre) is True
        assert _dans_fenetre(Date(2026, 6, 1), fenetre) is False


class TestTourMercato:
    def test_ouvre_une_negociation_pour_un_besoin_non_couvert(self, cfg: Config) -> None:
        monde, cible_id = _monde_avec_besoin_mc()

        tour_mercato(monde, cfg, Random(1))

        # seuil vendeur (cas de base, x1.35) > facteur_offre_initiale (x1.15) :
        # la premiere offre recoit une contre-offre, pas un accepte immediat.
        negos = [n for n in monde.negociations if n.joueur_id == cible_id]
        assert len(negos) == 1
        assert negos[0].club_acheteur_id == 1
        assert monde.joueurs[cible_id].club_id == 2  # pas encore transfere

    def test_negociation_converge_et_transfert_se_conclut(self, cfg: Config) -> None:
        monde, cible_id = _monde_avec_besoin_mc()
        rng = Random(1)

        tour_mercato(monde, cfg, rng)  # tour 1 : offre -> contre-offre
        assert monde.joueurs[cible_id].club_id == 2

        journal = tour_mercato(monde, cfg, rng)  # tour 2 : re-offre au montant contre -> accepte

        assert monde.joueurs[cible_id].club_id == 1
        assert monde.joueurs[cible_id].contrat is not None
        assert not any(n.joueur_id == cible_id for n in monde.negociations)
        assert any(e.type.value == "transfert" and e.joueur_id == cible_id for e in journal)
        assert len(monde.historique.transferts) == 1
        transfert = monde.historique.transferts[0]
        assert transfert.club_source_id == 2 and transfert.club_cible_id == 1
        assert transfert.montant > 0

    def test_transfert_deplace_le_budget_du_bon_montant(self, cfg: Config) -> None:
        monde, cible_id = _monde_avec_besoin_mc()
        rng = Random(1)
        budget_avant = monde.clubs[1].budget_transfert
        solde_avant = monde.clubs[2].solde

        tour_mercato(monde, cfg, rng)
        tour_mercato(monde, cfg, rng)

        montant = monde.historique.transferts[0].montant
        assert monde.clubs[1].budget_transfert == budget_avant - montant
        assert monde.clubs[2].solde == solde_avant + montant

    def test_budget_insuffisant_empeche_la_negociation(self, cfg: Config) -> None:
        monde, cible_id = _monde_avec_besoin_mc()
        monde.clubs[1].budget_transfert = 1  # ne peut rien s'offrir

        tour_mercato(monde, cfg, Random(1))

        assert monde.negociations == []
        assert monde.joueurs[cible_id].club_id == 2


class TestDemarchageSurplus:
    def test_vend_un_surplus_au_marche_exterieur(self, cfg: Config) -> None:
        club = un_club(id=1, reputation=10)  # cible basse : uniforme(60) ne cree que du surplus, pas de manque
        club_dormant = un_club(id=99, statut=StatutClub.DORMANT, budget_transfert=10_000_000)
        profondeur = profondeur_utile(Poste.BU, cfg)
        effectif = [un_joueur(id=100 + i, poste=Poste.BU, club_id=1, attributs=_uniforme(60)) for i in range(profondeur + 1)]
        surplus_id = effectif[-1].id  # dernier de l'effectif : le seul au-dela de la profondeur utile
        monde = un_monde(date=Date(2026, 8, 10), clubs={1: club, 99: club_dormant}, joueurs={j.id: j for j in effectif})

        journal = tour_mercato(monde, cfg, _RngDemarcheForce())

        assert monde.joueurs[surplus_id].club_id == 99
        assert any(e.type.value == "transfert" and e.joueur_id == surplus_id for e in journal)
        assert len(monde.historique.transferts) == 1
        transfert = monde.historique.transferts[0]
        assert transfert.club_source_id == 1 and transfert.club_cible_id == 99

    def test_ignore_un_club_dormant_trop_pauvre_pour_payer(self, cfg: Config) -> None:
        """Bug rapporte en production : un club dormant minuscule
        (budget_transfert quasi nul, comme un village a 800 places au
        stade) "achetait" des joueurs a plusieurs dizaines de millions —
        aucune verification de budget n'existait avant ce test."""
        club = un_club(id=1, reputation=10)
        club_dormant_pauvre = un_club(id=99, statut=StatutClub.DORMANT, budget_transfert=1)
        profondeur = profondeur_utile(Poste.BU, cfg)
        effectif = [un_joueur(id=100 + i, poste=Poste.BU, club_id=1, attributs=_uniforme(60)) for i in range(profondeur + 1)]
        surplus_id = effectif[-1].id
        monde = un_monde(date=Date(2026, 8, 10), clubs={1: club, 99: club_dormant_pauvre}, joueurs={j.id: j for j in effectif})

        tour_mercato(monde, cfg, _RngDemarcheForce())

        assert monde.joueurs[surplus_id].club_id == 1
        assert monde.historique.transferts == []

    def test_ne_demarche_pas_si_le_tirage_echoue(self, cfg: Config) -> None:
        club = un_club(id=1, reputation=10)
        club_dormant = un_club(id=99, statut=StatutClub.DORMANT, budget_transfert=10_000_000)
        profondeur = profondeur_utile(Poste.BU, cfg)
        effectif = [un_joueur(id=100 + i, poste=Poste.BU, club_id=1, attributs=_uniforme(60)) for i in range(profondeur + 1)]
        surplus_id = effectif[-1].id
        monde = un_monde(date=Date(2026, 8, 10), clubs={1: club, 99: club_dormant}, joueurs={j.id: j for j in effectif})

        tour_mercato(monde, cfg, _RngDemarcheRefuse())

        assert monde.joueurs[surplus_id].club_id == 1
        assert monde.historique.transferts == []

    def test_negociation_existante_est_reprise_en_priorite(self, cfg: Config) -> None:
        monde, cible_id = _monde_avec_besoin_mc()
        # negociation deja entamee au tour precedent, au seuil exact du
        # vendeur (surplus=0, patience=0 sur ce club) :
        # valeur * seuil_vendeur_multiplicateur.
        cfg_m = cfg.ia.mercato
        montant_seuil = math.ceil(valeur(monde.joueurs[cible_id], monde.date, cfg) * cfg_m.seuil_vendeur_multiplicateur)
        monde.negociations = [Negociation(club_acheteur_id=1, joueur_id=cible_id, montant_offert=montant_seuil, salaire_propose=50_000)]

        journal = tour_mercato(monde, cfg, Random(1))

        assert monde.joueurs[cible_id].club_id == 1
        assert any(e.type.value == "transfert" for e in journal)
