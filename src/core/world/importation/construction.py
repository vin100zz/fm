"""Raw CSV rows -> domain entities.

Includes the v0 synthesis for fields the source data doesn't provide
(player attributes/potentiel, club reputation/budgets) — see
config/import.json and "Données fournies par l'utilisateur" in
docs/modele-donnees.md. Isolated here so it can be swapped for a direct
mapping the day real data is available, without touching lecteurs.py,
perimetre.py or validation.py.
"""

import math
from random import Random

from core.config.modeles.ia_gestion import BudgetsConfig, PersonnaliteClubConfig, ValorisationConfig
from core.config.modeles.import_donnees import SyntheseAttributsConfig, SyntheseClubConfig
from core.config.modeles.monde import ConfigMonde
from core.config.modeles.racine import Config
from core.domain.club import Club, PersonnaliteClub, StatutClub
from core.domain.competition import Competition
from core.domain.contrat import Contrat
from core.domain.date import Date
from core.domain.joueur import Joueur
from core.domain.poste import Poste
from core.world.generation_attributs import generer_attributs_depuis_niveau
from core.world.importation.perimetre import determiner_statut, trouver_competition
from core.world.importation.postes_fm import parser_postes
from core.world.progression import facteur_par_age

_LONGUEUR_MAX_NOM_COURT = 20


def construire_club(ligne: dict[str, str], cfg: Config, rng: Random) -> Club:
    club_id = int(ligne["Unique ID"])
    division_id = int(ligne["Division ID"])
    nom = ligne["Name"]
    stad_cap = int(ligne["Stad Cap"])

    statut = determiner_statut(division_id, cfg.monde)
    competition = trouver_competition(division_id, cfg.monde)
    # Active clubs get the ISO pays code from config; dormant clubs (the
    # vast majority, ~1700 foreign leagues) keep the source's free-text
    # nation name — see docs/modele-donnees.md.
    pays = competition.pays if competition is not None else ligne["Nation"]

    reputation = _reputation_depuis_stade(stad_cap, cfg.import_donnees.synthese_club, rng)
    note_centre_formation = _note_centre_formation(reputation, cfg.import_donnees.synthese_club, rng)
    budget_transfert, masse_salariale_max = _budgets_initiaux(reputation, pays, cfg.ia.budgets)

    return Club(
        id=club_id,
        nom=nom,
        nom_court=nom[:_LONGUEUR_MAX_NOM_COURT],
        pays=pays,
        competition_id=division_id,
        statut=statut,
        reputation=reputation,
        note_centre_formation=note_centre_formation,
        budget_transfert=budget_transfert,
        masse_salariale_max=masse_salariale_max,
        solde=0,
        formation_preferee=rng.choice(list(cfg.formations.formations)),
        personnalite=_tirer_personnalite(cfg.ia.personnalite_club, rng),
    )


def _reputation_depuis_stade(stad_cap: int, cfg: SyntheseClubConfig, rng: Random) -> int:
    plage_cap, plage_rep = cfg.stad_cap_reference, cfg.reputation
    cap = max(stad_cap, 1)
    log_min, log_max = math.log(max(plage_cap.min, 1)), math.log(plage_cap.max)
    ratio = min(max((math.log(cap) - log_min) / (log_max - log_min), 0.0), 1.0)
    base = plage_rep.min + ratio * (plage_rep.max - plage_rep.min)
    bruit = rng.gauss(0.0, cfg.reputation_bruit_ecart_type)
    return round(min(max(base + bruit, plage_rep.min), plage_rep.max))


def _note_centre_formation(reputation: int, cfg: SyntheseClubConfig, rng: Random) -> int:
    plage = cfg.note_centre_formation
    base = reputation * cfg.note_centre_formation_facteur_reputation
    bruit = rng.gauss(0.0, cfg.note_centre_formation_bruit_ecart_type)
    return round(min(max(base + bruit, plage.min), plage.max))


def _budgets_initiaux(reputation: int, pays: str, cfg: BudgetsConfig) -> tuple[int, int]:
    revenus = cfg.revenus
    multiplicateur = revenus.multiplicateur_pays.get(pays, 1.0)
    revenus_estimes = reputation * revenus.base_par_point_reputation * multiplicateur
    budget_transfert = round(revenus_estimes * cfg.part_revenus_transfert)
    masse_salariale_max = round(revenus_estimes * cfg.part_revenus_salaires / cfg.semaines_par_an)
    return budget_transfert, masse_salariale_max


def _tirer_personnalite(cfg: PersonnaliteClubConfig, rng: Random) -> PersonnaliteClub:
    # correlation_reputation_agressivite is not applied yet: nothing reads
    # club personality meaningfully before the AI step (step 7), a plain
    # uniform draw is good enough until then.
    return PersonnaliteClub(
        appetit_risque=rng.uniform(cfg.appetit_risque.min, cfg.appetit_risque.max),
        preference_jeunes=rng.uniform(cfg.preference_jeunes.min, cfg.preference_jeunes.max),
        agressivite_salariale=rng.uniform(cfg.agressivite_salariale.min, cfg.agressivite_salariale.max),
        patience_negociation=rng.uniform(cfg.patience_negociation.min, cfg.patience_negociation.max),
    )


def construire_competitions(clubs: dict[int, Club], cfg_monde: ConfigMonde) -> dict[int, Competition]:
    competitions: dict[int, Competition] = {}
    for competition_cfg in cfg_monde.competitions_simulees:
        club_ids = [
            club.id
            for club in clubs.values()
            if club.statut is StatutClub.ACTIF and club.competition_id == competition_cfg.division_id
        ]
        competitions[competition_cfg.division_id] = Competition(
            id=competition_cfg.division_id,
            nom=competition_cfg.nom,
            pays=competition_cfg.pays,
            niveau=competition_cfg.niveau,
            club_ids=club_ids,
        )
    return competitions


def construire_joueur(
    ligne: dict[str, str], cfg: Config, date_debut: Date, rng: Random, avertissements: list[str]
) -> Joueur:
    joueur_id = int(ligne["Unique ID"])
    nom, prenom = _separer_nom(ligne["Name"])
    nationalite = ligne["Nation"].split("/")[0].strip()
    date_naissance = Date.depuis_jj_mm_aaaa(ligne["Date Of Birth"])
    age = date_naissance.age_a(date_debut)

    poste, postes_secondaires = parser_postes(
        ligne["Position"], cfg.import_donnees.postes.affinite_secondaire_defaut
    )

    valeur_marche = _valeur_marche(ligne["Value"])
    niveau = _niveau_depuis_valeur(
        valeur_marche, age, poste, cfg.ia.valorisation, cfg.import_donnees.synthese_attributs
    )
    attributs = generer_attributs_depuis_niveau(niveau, poste, cfg.attributs, rng)
    potentiel = _potentiel_depuis_niveau(niveau, age, cfg.import_donnees.synthese_attributs)

    club_id_brut = int(ligne["Club ID"])
    club_id = club_id_brut if club_id_brut != -1 else None
    contrat = _construire_contrat(ligne, club_id, joueur_id, date_debut, avertissements)

    return Joueur(
        id=joueur_id,
        nom=nom,
        prenom=prenom,
        nationalite=nationalite,
        date_naissance=date_naissance,
        poste=poste,
        attributs=attributs,
        potentiel=potentiel,
        forme=cfg.etats.forme.initiale,
        fatigue=cfg.etats.fatigue.initiale,
        moral=cfg.etats.moral.initial,
        fragilite=rng.uniform(cfg.etats.blessures.fragilite_min, cfg.etats.blessures.fragilite_max),
        postes_secondaires=postes_secondaires,
        club_id=club_id,
        contrat=contrat,
    )


def _separer_nom(nom_complet: str) -> tuple[str, str]:
    """Source format is "Lastname, Firstname", except mononyms ("Alisson")."""
    if "," in nom_complet:
        nom, _, prenom = nom_complet.partition(",")
        return nom.strip(), prenom.strip()
    return nom_complet.strip(), ""


def _valeur_marche(brut: str) -> float | None:
    valeur = int(brut)
    return float(valeur) if valeur > 0 else None


def _niveau_depuis_valeur(
    valeur_marche: float | None,
    age: int,
    poste: Poste,
    cfg_valorisation: ValorisationConfig,
    cfg_synthese: SyntheseAttributsConfig,
) -> float:
    """Approximate a level by inverting ia_gestion.valorisation. Known
    limitation, documented in docs/modele-donnees.md: this makes the
    valorisation benchmark partially circular until real attributes
    replace this synthesis.
    """
    plage = cfg_synthese.niveau
    if valeur_marche is None:
        return plage.min

    facteur_age = facteur_par_age(age, cfg_valorisation.courbe_age)
    rarete = cfg_valorisation.rarete_poste.get(poste.value, 1.0)
    denominateur = cfg_valorisation.base_euros * facteur_age * rarete
    if denominateur <= 0:
        return plage.min

    niveau = cfg_valorisation.niveau_reference + math.log(valeur_marche / denominateur) / cfg_valorisation.exposant
    return min(max(niveau, plage.min), plage.max)


def _potentiel_depuis_niveau(niveau: float, age: int, cfg: SyntheseAttributsConfig) -> int:
    proximite_jeunesse = min(max((cfg.marge_potentiel_age_seuil - age) / cfg.marge_potentiel_age_seuil, 0.0), 1.0)
    marge = cfg.marge_potentiel_defaut + cfg.marge_potentiel_jeune_max * proximite_jeunesse
    return round(min(niveau + marge, 100))


def _construire_contrat(
    ligne: dict[str, str],
    club_id: int | None,
    joueur_id: int,
    date_debut: Date,
    avertissements: list[str],
) -> Contrat | None:
    brut_fin = ligne["Contract End"]
    if club_id is None or brut_fin == "-":
        return None

    date_fin = Date.depuis_jj_mm_aaaa(brut_fin)
    if date_fin < date_debut:
        avertissements.append(
            f"joueur {joueur_id}: fin de contrat {date_fin} anterieure au debut de partie, reportee d'un an"
        )
        date_fin = date_fin.plus_un_an()

    salaire_hebdo = max(int(ligne["Wage"]), 0)
    return Contrat(salaire_hebdo=salaire_hebdo, date_fin=date_fin, date_signature=date_debut)
