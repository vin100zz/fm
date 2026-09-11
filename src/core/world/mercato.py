"""The transfer window loop — "Boucle de mercato" in docs/ia-gestion.md,
built on the pure decision primitives from `core/ai/mercato.py` and
`core/ai/contrats.py` that had nothing calling them until now.

**Structure follows the doc's three-phase turn exactly**: every active
club's intentions are computed against the state at the *start* of the
turn (`tour_mercato` builds one `pool_par_poste` snapshot and only
mutates `Monde` in the final resolution pass) — "tous les clubs jouent
le même tour avant que quoi que ce soit ne se résolve", so the first
club processed can't out-compete the others just by going first.

**Negotiations converge in at most two rounds by construction**:
`repondre_offre` is a pure function of the offer amount, so re-offering
at exactly the `contre_montant` it just returned reproduces the same
threshold and clears it — `tours_negociation_max`
(`config/ia_gestion.json`) is a safety net for the one case that
*doesn't* converge (the counter becomes unaffordable), not the normal
path.

**Deliberately out of scope** (documented, not silently skipped):
- Dormant clubs never *initiate* offers — docs mentions them
  "démarchant" active clubs' surplus/expiring players
  (`ia_gestion.mercato.clubs_dormants.probabilite_demarchage_par_fenetre`
  is defined but unused); only the reactive side
  (`core.ai.mercato.repondre_offre_dormant`) is wired in.
- Free agents and weekly contract renewals (docs §6, "Agents libres")
  aren't part of this loop — `core.ai.contrats.decision_renouvellement`
  exists but nothing calls it on a schedule yet, so a player's contract
  never actually expires into free agency.
- No loan/swap deals, no release clauses — see `RegleTransfert` in
  docs/architecture.md, `TransfertSec` (straight cash) is the only kind.

**Performance**: three changes bring one real-dataset turn (96 active
clubs) from ~15s down to ~1.2s. `_pool_par_poste` sorts each poste's
~32 000-player pool by level once per turn; `_meilleur_candidat` then
narrows to a small window around the buying club's target level with
`bisect` instead of sorting or scanning the full pool per need.
`core.ai.utilite.utilite`'s optional `sans` parameter avoids
recomputing the club's own unchanged best-XI rating once per shortlist
candidate. And `tentatives_prospection_max` caps how many needs a club
re-evaluates once nothing viable turns up — a squad already near
attribute-scale saturation (a top club under the v0 synthesis, see
docs/modele-donnees.md) can have a dozen `MANQUE` entries that never
yield a positive `utilite()`, and re-trying all of them every turn was
most of the remaining cost. `taille_shortlist`/`tentatives_prospection_max`
were also turned down from their step-7 defaults (12/unset) to 6/4:
`meilleure_affectation` inside each `utilite()` call is the one
irreducibly expensive part per candidate (no cache — `Joueur` isn't
hashable, and `note_globale` is called throughout `core/engine` on
live, changing attributes, so caching it globally risks going stale),
so shortlist width is the last lever cheap enough to turn without
touching shared engine code.
"""

from bisect import bisect_left
from collections import defaultdict
from random import Random

from core.ai.besoins import evaluer_besoins, niveau_cible
from core.ai.contrats import duree_par_age, salaire_attendu
from core.ai.mercato import repondre_offre, repondre_offre_dormant, score_offre
from core.ai.utilite import note_meilleur_onze, utilite
from core.ai.valorisation import valeur
from core.config.modeles.monde import FenetreMercato
from core.config.modeles.racine import Config
from core.domain.besoin import TypeBesoin
from core.domain.club import Club, StatutClub
from core.domain.contrat import Contrat
from core.domain.date import Date
from core.domain.historique import TransfertHistorique
from core.domain.joueur import Joueur
from core.domain.journal import EvenementJour, TypeEvenementJour
from core.domain.monde import Monde
from core.domain.negociation import Negociation
from core.domain.offre import Offre, TypeReponse
from core.domain.poste import Poste
from core.world.note_globale import note_globale


def fenetre_mercato_ouverte(date: Date, cfg: Config) -> bool:
    cfg_m = cfg.monde.mercato
    return _dans_fenetre(date, cfg_m.ete) or _dans_fenetre(date, cfg_m.hiver)


def avancer_mercato(monde: Monde, cfg: Config, rng: Random) -> list[EvenementJour]:
    if not fenetre_mercato_ouverte(monde.date, cfg):
        return []
    journal: list[EvenementJour] = []
    for _ in range(cfg.monde.mercato.tours_par_jour):
        journal += tour_mercato(monde, cfg, rng)
    return journal


def tour_mercato(monde: Monde, cfg: Config, rng: Random) -> list[EvenementJour]:
    cfg_m = cfg.ia.mercato
    pool_par_poste = _pool_par_poste(monde, cfg)

    # joueur_id -> [(Negociation, Offre), ...] — un joueur peut recevoir
    # des offres de plusieurs acheteurs le meme tour.
    offres_par_joueur: dict[int, list[tuple[Negociation, Offre]]] = defaultdict(list)
    negociations_conservees: list[Negociation] = []

    for club in monde.clubs.values():
        if club.statut is not StatutClub.ACTIF:
            continue

        effectif = _effectif(monde, club.id)
        negos_du_club = [n for n in monde.negociations if n.club_acheteur_id == club.id]
        montant_reserve = sum(n.montant_offert for n in negos_du_club)
        salaire_reserve = sum(n.salaire_propose for n in negos_du_club)
        cibles_visees = {n.joueur_id for n in negos_du_club}

        for negociation in negos_du_club:
            joueur = monde.joueurs.get(negociation.joueur_id)
            if joueur is None or joueur.club_id == club.id:
                continue
            offre = Offre(joueur.id, club.id, negociation.montant_offert, negociation.salaire_propose)
            offres_par_joueur[joueur.id].append((negociation, offre))

        places_libres = cfg_m.negociations_actives_max - len(negos_du_club)
        if places_libres <= 0:
            continue

        sans_actuel = note_meilleur_onze(effectif, club.formation_preferee, cfg)
        tentatives = 0

        for besoin in evaluer_besoins(club, effectif, cfg):
            if places_libres <= 0 or tentatives >= cfg_m.tentatives_prospection_max:
                break
            if besoin.type is not TypeBesoin.MANQUE:
                continue
            tentatives += 1

            candidat = _meilleur_candidat(club, besoin.poste, effectif, cibles_visees, pool_par_poste, monde, cfg, sans_actuel)
            if candidat is None:
                continue

            montant = round(valeur(candidat, monde.date, cfg) * cfg_m.facteur_offre_initiale)
            salaire = salaire_attendu(candidat, monde.date, cfg)
            if not _peut_se_permettre(club, montant, salaire, effectif, cfg, montant_reserve, salaire_reserve):
                cibles_visees.add(candidat.id)  # inabordable : ne pas le re-evaluer ce tour
                continue

            negociation = Negociation(club.id, candidat.id, montant, salaire)
            offre = Offre(candidat.id, club.id, montant, salaire)
            offres_par_joueur[candidat.id].append((negociation, offre))
            cibles_visees.add(candidat.id)
            montant_reserve += montant
            salaire_reserve += salaire
            places_libres -= 1

    journal = _resoudre_offres(monde, offres_par_joueur, negociations_conservees, cfg, rng)
    monde.negociations = negociations_conservees
    return journal


def _resoudre_offres(
    monde: Monde,
    offres_par_joueur: dict[int, list[tuple[Negociation, Offre]]],
    negociations_conservees: list[Negociation],
    cfg: Config,
    rng: Random,
) -> list[EvenementJour]:
    cfg_m = cfg.ia.mercato
    journal: list[EvenementJour] = []

    for joueur_id, propositions in offres_par_joueur.items():
        joueur = monde.joueurs[joueur_id]
        club_vendeur = monde.clubs.get(joueur.club_id) if joueur.club_id is not None else None
        if club_vendeur is None:
            continue
        effectif_vendeur = _effectif(monde, club_vendeur.id)

        acceptees: list[tuple[Negociation, Offre, Club]] = []
        for negociation, offre in propositions:
            club_acheteur = monde.clubs[negociation.club_acheteur_id]
            if club_vendeur.statut is StatutClub.ACTIF:
                reponse = repondre_offre(offre, club_vendeur, joueur, effectif_vendeur, monde.date, cfg)
            else:
                reponse = repondre_offre_dormant(offre, joueur, monde.date, cfg, rng)

            if reponse.type is TypeReponse.ACCEPTE:
                acceptees.append((negociation, offre, club_acheteur))
            elif reponse.type is TypeReponse.CONTRE_OFFRE and negociation.tours + 1 < cfg_m.tours_negociation_max:
                effectif_acheteur = _effectif(monde, club_acheteur.id)
                if _peut_se_permettre(club_acheteur, reponse.contre_montant, negociation.salaire_propose, effectif_acheteur, cfg):
                    negociations_conservees.append(
                        Negociation(club_acheteur.id, joueur_id, reponse.contre_montant, negociation.salaire_propose, negociation.tours + 1)
                    )
                # inabordable ou tours epuises : negociation abandonnee (rien reconduit)

        if not acceptees:
            continue

        gagnante = acceptees[0] if len(acceptees) == 1 else max(
            acceptees,
            key=lambda a: score_offre(joueur, a[2], a[1].salaire_propose, _effectif(monde, a[2].id), monde.date, cfg, rng),
        )
        _, offre_gagnante, club_acheteur_gagnant = gagnante
        journal.append(_executer_transfert(monde, joueur, club_vendeur, club_acheteur_gagnant, offre_gagnante, cfg))

    return journal


def _pool_par_poste(monde: Monde, cfg: Config) -> dict[Poste, list[tuple[float, Joueur]]]:
    """(note_globale, joueur) pairs, sorted by note ascending — built once
    per turn so `_meilleur_candidat` can `bisect` straight to a club's
    target level instead of sorting or scanning the whole poste pool for
    every single need, of every one of the ~96 clubs.
    """
    pool: dict[Poste, list[tuple[float, Joueur]]] = defaultdict(list)
    for joueur in monde.joueurs.values():
        if joueur.club_id is not None:
            pool[joueur.poste].append((note_globale(joueur, cfg.attributs), joueur))
    for candidats in pool.values():
        candidats.sort(key=lambda paire: paire[0])
    return pool


def _meilleur_candidat(
    club: Club,
    poste: Poste,
    effectif: list[Joueur],
    cibles_visees: set[int],
    pool_par_poste: dict[Poste, list[tuple[float, Joueur]]],
    monde: Monde,
    cfg: Config,
    sans_actuel: float,
) -> Joueur | None:
    """Only the (real, expensive — a `meilleure_affectation` call each)
    marginal utility of a bounded shortlist gets computed: a window
    around the club's target level in the pre-sorted poste pool, wide
    enough to still yield `taille_shortlist` candidates after excluding
    the buyer's own players and this turn's already-targeted ones.
    `sans_actuel` (the squad's own best-XI rating) is the same for every
    candidate at this club this turn — computed once by the caller
    rather than once per candidate (`core.ai.utilite.utilite`'s `sans`
    parameter).
    """
    candidats_tries = pool_par_poste.get(poste)
    if not candidats_tries:
        return None

    cible = niveau_cible(club, cfg)
    taille = cfg.ia.mercato.taille_shortlist
    notes = [note for note, _ in candidats_tries]
    centre = bisect_left(notes, cible)
    fenetre = taille * 3
    voisinage = candidats_tries[max(0, centre - fenetre) : centre + fenetre]

    candidats = [j for _, j in voisinage if j.club_id != club.id and j.id not in cibles_visees]
    candidats.sort(key=lambda j: abs(note_globale(j, cfg.attributs) - cible))
    shortlist = candidats[:taille]

    meilleur, meilleur_gain = None, 0.0
    for candidat in shortlist:
        gain = utilite(candidat, club, effectif, monde.date, cfg, sans=sans_actuel)
        if gain > meilleur_gain:
            meilleur, meilleur_gain = candidat, gain
    return meilleur


def _peut_se_permettre(
    club: Club, montant: int, salaire: int, effectif: list[Joueur], cfg: Config,
    montant_reserve: int = 0, salaire_reserve: int = 0,
) -> bool:
    if montant + montant_reserve > club.budget_transfert:
        return False
    if not cfg.ia.garde_fous.plafond_salarial_strict:
        return True
    masse_actuelle = sum(j.contrat.salaire_hebdo for j in effectif if j.contrat is not None)
    return masse_actuelle + salaire + salaire_reserve <= club.masse_salariale_max


def _executer_transfert(monde: Monde, joueur: Joueur, club_vendeur: Club, club_acheteur: Club, offre: Offre, cfg: Config) -> EvenementJour:
    montant = offre.montant
    club_acheteur.budget_transfert = max(club_acheteur.budget_transfert - montant, 0)
    if club_vendeur.statut is StatutClub.ACTIF:
        club_vendeur.solde += montant

    duree = duree_par_age(joueur.date_naissance.age_a(monde.date), cfg.ia.contrats)
    joueur.club_id = club_acheteur.id
    joueur.contrat = Contrat(
        salaire_hebdo=offre.salaire_propose,
        date_fin=Date(monde.date.annee + duree, monde.date.mois, monde.date.jour),
        date_signature=monde.date,
    )

    monde.historique.transferts.append(
        TransfertHistorique(
            date=monde.date, joueur_id=joueur.id, club_source_id=club_vendeur.id, club_cible_id=club_acheteur.id,
            montant=montant, saison=monde.saison,
        )
    )
    description = f"{joueur.prenom} {joueur.nom} : {club_vendeur.nom} -> {club_acheteur.nom} ({montant} €)"
    return EvenementJour(TypeEvenementJour.TRANSFERT, description, joueur_id=joueur.id)


def _effectif(monde: Monde, club_id: int) -> list[Joueur]:
    return [j for j in monde.joueurs.values() if j.club_id == club_id]


def _dans_fenetre(date: Date, fenetre: FenetreMercato) -> bool:
    debut = (fenetre.debut_mois, fenetre.debut_jour)
    fin = (fenetre.fin_mois, fenetre.fin_jour)
    actuel = (date.mois, date.jour)
    if debut <= fin:
        return debut <= actuel <= fin
    return actuel >= debut or actuel <= fin  # fenetre a cheval sur le nouvel an
