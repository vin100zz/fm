from core.ai.besoins import niveau_cible
from core.ai.contrats import decision_renouvellement, salaire_attendu, satisfaction
from core.ai.utilite import utilite
from core.config import Config
from core.domain.attributs import Attributs
from core.domain.contrat import Contrat
from core.domain.date import Date
from core.domain.poste import Poste
from core.world.note_globale import note_globale
from tests.unit.world.fabriques_domaine import DATE, des_attributs, un_club, un_joueur


def _uniforme(note: int) -> Attributs:
    return des_attributs(**{champ: note for champ in Attributs.__dataclass_fields__})


def test_salaire_attendu_croit_avec_le_niveau(cfg: Config) -> None:
    faible = un_joueur(id=1, attributs=_uniforme(50), potentiel=50)
    fort = un_joueur(id=2, attributs=_uniforme(85), potentiel=85)
    assert salaire_attendu(fort, DATE, cfg) > salaire_attendu(faible, DATE, cfg)


def test_satisfaction_croit_avec_le_salaire(cfg: Config) -> None:
    sous_paye = un_joueur(id=1, attributs=_uniforme(70), contrat=Contrat(1_000, Date(2028, 6, 30), DATE))
    bien_paye = un_joueur(
        id=2, attributs=_uniforme(70),
        contrat=Contrat(salaire_attendu(sous_paye, DATE, cfg), Date(2028, 6, 30), DATE),
    )
    club = un_club(reputation=60)

    sat_faible = satisfaction(sous_paye, club, minutes_saison=1000, minutes_attendues=1000, date_actuelle=DATE, cfg=cfg)
    sat_forte = satisfaction(bien_paye, club, minutes_saison=1000, minutes_attendues=1000, date_actuelle=DATE, cfg=cfg)
    assert sat_forte > sat_faible


def test_satisfaction_croit_avec_le_temps_de_jeu(cfg: Config) -> None:
    joueur = un_joueur(id=1, attributs=_uniforme(70), contrat=Contrat(50_000, Date(2028, 6, 30), DATE))
    club = un_club(reputation=60)

    peu_de_temps = satisfaction(joueur, club, minutes_saison=200, minutes_attendues=2000, date_actuelle=DATE, cfg=cfg)
    beaucoup_de_temps = satisfaction(joueur, club, minutes_saison=1900, minutes_attendues=2000, date_actuelle=DATE, cfg=cfg)
    assert beaucoup_de_temps > peu_de_temps


def test_decision_renouvellement_pas_de_negociation_si_satisfait_et_loin_de_l_echeance(cfg: Config) -> None:
    joueur = un_joueur(id=1, attributs=_uniforme(70), potentiel=70)
    joueur.contrat = Contrat(salaire_attendu(joueur, DATE, cfg), Date(2032, 6, 30), DATE)
    club = un_club(reputation=round(note_globale(joueur, cfg.attributs)), masse_salariale_max=10**9)

    decision = decision_renouvellement(
        joueur, club, effectif=[], minutes_saison=1000, minutes_attendues=1000, date_actuelle=DATE, cfg=cfg
    )
    assert decision.ouvre_negociation is False


def test_decision_renouvellement_renouvelle_si_sous_paye_et_sous_le_plafond(cfg: Config) -> None:
    joueur = un_joueur(id=1, attributs=_uniforme(70), potentiel=70, contrat=Contrat(1_000, Date(2032, 6, 30), DATE))
    club = un_club(reputation=80, masse_salariale_max=10**9)

    decision = decision_renouvellement(
        joueur, club, effectif=[], minutes_saison=1000, minutes_attendues=1000, date_actuelle=DATE, cfg=cfg
    )
    assert decision.ouvre_negociation is True
    assert decision.renouvelle is True
    assert decision.salaire_demande > joueur.contrat.salaire_hebdo


def test_decision_renouvellement_renouvelle_si_le_joueur_reste_au_niveau_meme_si_lutilite_est_nulle(cfg: Config) -> None:
    """Meme cause que core/world/mercato.py::_meilleur_candidat
    (2026-09-11) : utilite() passe par meilleure_affectation, gloutonne —
    un effectif deja sature au meme niveau que le joueur evalue peut
    montrer un gain marginal nul, meme si ce joueur merite clairement sa
    place. Repere en production : les plus grands clubs (Real Madrid,
    Barcelone, Man City) s'effondraient specifiquement pour cette raison,
    leurs propres bons joueurs jamais renouveles."""
    club = un_club(reputation=70, masse_salariale_max=10**9)
    niveau = round(niveau_cible(club, cfg))
    effectif_sans_lui = [un_joueur(id=100 + i, poste=Poste.MC, club_id=club.id, attributs=_uniforme(niveau)) for i in range(10)]
    joueur = un_joueur(
        id=1, poste=Poste.MC, club_id=club.id, attributs=_uniforme(niveau), potentiel=niveau,
        contrat=Contrat(salaire_attendu(un_joueur(attributs=_uniforme(niveau)), DATE, cfg), Date(2027, 3, 1), DATE),
    )

    gain = utilite(joueur, club, effectif_sans_lui, DATE, cfg)
    assert gain <= 0  # confirme que ce cas reproduit bien le bruit de meilleure_affectation

    decision = decision_renouvellement(
        joueur, club, effectif_sans_lui, minutes_saison=0, minutes_attendues=0, date_actuelle=DATE, cfg=cfg
    )
    assert decision.renouvelle is True


def test_decision_renouvellement_pas_de_renouvellement_si_plafond_depasse(cfg: Config) -> None:
    joueur = un_joueur(id=1, attributs=_uniforme(90), potentiel=90, contrat=Contrat(1_000, Date(2032, 6, 30), DATE))
    club = un_club(reputation=90, masse_salariale_max=1)

    decision = decision_renouvellement(
        joueur, club, effectif=[], minutes_saison=1000, minutes_attendues=1000, date_actuelle=DATE, cfg=cfg
    )
    assert decision.ouvre_negociation is True
    assert decision.renouvelle is False
