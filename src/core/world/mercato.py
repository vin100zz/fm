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

**Volume calibration (2026-09-11, revised)**: measured at 12 transfers
for a full season across the 96 active clubs, far under the 2-7
arrivals+departures per club real football suggests. Two compounding
causes, both fixed — see `_meilleur_candidat` (acceptance criterion)
and `_demarcher_surplus`/`_resoudre_demarchages` (proactive selling)
below, and `config/ia_gestion.json`'s `profil_cible`/`clubs_dormants`
`_note`s for the numbers.

**Deliberately out of scope** (documented, not silently skipped):
- Free agents and weekly contract renewals (docs §6, "Agents libres")
  aren't part of this loop — `core.ai.contrats.decision_renouvellement`
  exists but nothing calls it on a schedule yet, so a player's contract
  never actually expires into free agency.
- No loan/swap deals, no release clauses — see `RegleTransfert` in
  docs/architecture.md, `TransfertSec` (straight cash) is the only kind.
- A dormant club never negotiates or shows up as a specific persistent
  identity beyond the transfer record — `_demarcher_surplus` picks one
  uniformly at random as a destination, since none of the ~25 900 are
  individually simulated (docs/modele-donnees.md's actif/dormant split).

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

from core.ai.besoins import evaluer_besoins, evaluer_opportunites
from core.ai.budgets import masse_salariale_actuelle
from core.ai.contrats import duree_par_age, salaire_attendu
from core.ai.mercato import repondre_offre, repondre_offre_dormant, score_offre
from core.ai.utilite import note_meilleur_onze, utilite
from core.ai.valorisation import valeur
from core.config.modeles.monde import FenetreMercato
from core.config.modeles.racine import Config
from core.domain.besoin import Besoin, TypeBesoin
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
    clubs_dormants_tries = _clubs_dormants_tries_par_budget(monde)

    # joueur_id -> [(Negociation, Offre), ...] — un joueur peut recevoir
    # des offres de plusieurs acheteurs le meme tour.
    offres_par_joueur: dict[int, list[tuple[Negociation, Offre]]] = defaultdict(list)
    negociations_conservees: list[Negociation] = []
    demarchages: list[tuple[Joueur, Club, Club, Offre]] = []

    for club in monde.clubs.values():
        if club.statut is not StatutClub.ACTIF:
            continue

        effectif = _effectif(monde, club.id)
        besoins = evaluer_besoins(club, effectif, cfg)
        demarchages.extend(_demarcher_surplus(club, besoins, monde, clubs_dormants_tries, cfg, rng))

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

        manques = [b for b in besoins if b.type is TypeBesoin.MANQUE]
        besoins_a_examiner = manques + evaluer_opportunites(club, effectif, cfg)

        for besoin in besoins_a_examiner:
            if places_libres <= 0 or tentatives >= cfg_m.tentatives_prospection_max:
                break
            tentatives += 1

            candidat = _meilleur_candidat(club, besoin, effectif, cibles_visees, pool_par_poste, monde, cfg, sans_actuel)
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
    journal += _resoudre_demarchages(monde, demarchages, cfg)
    return journal


def _demarcher_surplus(
    club: Club, besoins: list[Besoin], monde: Monde, clubs_dormants_tries: list[Club], cfg: Config, rng: Random,
) -> list[tuple[Joueur, Club, Club, Offre]]:
    """Le marché extérieur approche les joueurs surplus d'un club actif —
    "le club vend les surplus pour financer les manques" (docs/ia-gestion.md
    §3) restait vrai côté détection (`TypeBesoin.SURPLUS` existe depuis
    l'étape 7) mais mort côté action : rien ne vendait jamais, un club
    proche de son plafond salarial ne s'en dégageait donc jamais (mesuré :
    c'est devenu le premier goulot du volume de transferts une fois la
    prospection élargie, voir `clubs_dormants._note`). Même simplification
    que `repondre_offre_dormant` : un tirage, pas de négociation — un club
    dormant précis n'a pas de sens à modéliser individuellement (import
    validation.py les autorise vides/incomplets, cf. docs/modele-donnees.md).

    **La destination reste bornée par son propre `budget_transfert`
    (2026-09-11, corrigé)** : le premier jet tirait un club dormant
    uniformément parmi les ~25 900 sans regarder s'il pouvait payer, ce
    qui produisait des transferts absurdes (un village de 800 places au
    stade "signant" un joueur à 130M€, repéré par l'utilisateur en
    production). `budget_transfert` est calculé pour les clubs dormants
    exactement comme pour les actifs (`construction.py`, dérivé de la
    réputation/capacité du stade) — un filtre dessus suffit, pas besoin
    d'inventer une notion de richesse séparée pour le marché extérieur.
    """
    if not clubs_dormants_tries:
        return []
    cfg_d = cfg.ia.mercato.clubs_dormants
    budgets = [c.budget_transfert for c in clubs_dormants_tries]
    demarchages: list[tuple[Joueur, Club, Club, Offre]] = []
    for besoin in besoins:
        if besoin.type is not TypeBesoin.SURPLUS:
            continue
        if rng.random() >= cfg_d.probabilite_demarchage_par_tour:
            continue
        joueur = monde.joueurs.get(besoin.joueur_id)
        if joueur is None or joueur.club_id != club.id:
            continue
        montant = round(valeur(joueur, monde.date, cfg) * cfg_d.multiplicateur_prix_demande)
        candidats = clubs_dormants_tries[bisect_left(budgets, montant):]
        if not candidats:
            continue  # aucun club dormant ne peut se permettre ce joueur
        club_dormant = rng.choice(candidats)
        salaire = salaire_attendu(joueur, monde.date, cfg)
        demarchages.append((joueur, club, club_dormant, Offre(joueur.id, club_dormant.id, montant, salaire)))
    return demarchages


def _clubs_dormants_tries_par_budget(monde: Monde) -> list[Club]:
    """Trié une fois par tour pour que `_demarcher_surplus` puisse
    `bisect` directement vers les clubs assez riches pour un montant
    donné, plutôt que de filtrer les ~25 900 clubs dormants à chaque
    joueur démarché."""
    return sorted(
        (c for c in monde.clubs.values() if c.statut is StatutClub.DORMANT),
        key=lambda c: c.budget_transfert,
    )


def _resoudre_demarchages(
    monde: Monde, demarchages: list[tuple[Joueur, Club, Club, Offre]], cfg: Config,
) -> list[EvenementJour]:
    """Executé après `_resoudre_offres` : un joueur démarché par le
    marché extérieur peut aussi avoir été vendu ce même tour via une
    négociation classique (`joueur.club_id` a alors déjà changé) — dans
    ce cas le démarchage est simplement ignoré plutôt que de vendre le
    joueur une seconde fois.
    """
    journal: list[EvenementJour] = []
    for joueur, club_vendeur, club_dormant, offre in demarchages:
        if joueur.club_id != club_vendeur.id:
            continue
        journal.append(_executer_transfert(monde, joueur, club_vendeur, club_dormant, offre, cfg))
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
    besoin: Besoin,
    effectif: list[Joueur],
    cibles_visees: set[int],
    pool_par_poste: dict[Poste, list[tuple[float, Joueur]]],
    monde: Monde,
    cfg: Config,
    sans_actuel: float,
) -> Joueur | None:
    """Only the (real, expensive — a `meilleure_affectation` call each)
    marginal utility of a bounded shortlist gets computed: a window
    around `besoin.niveau_attendu` (the bar this specific besoin needs
    cleared — not the club's generic titulaire-tier target, which would
    center the search wrong for a rotation/doublure/opportuniste besoin)
    in the pre-sorted poste pool, wide enough to still yield
    `taille_shortlist` candidates after excluding the buyer's own
    players and this turn's already-targeted ones. `sans_actuel` (the
    squad's own best-XI rating) is the same for every candidate at this
    club this turn — computed once by the caller rather than once per
    candidate (`core.ai.utilite.utilite`'s `sans` parameter).

    **Acceptance (2026-09-11, revised)**: a candidat is accepted if it
    clears `besoin.niveau_attendu` directly, OR if `utilite()` — the
    marginal best-XI gain — is positive on its own. The direct check is
    the one that matters most: `utilite()` routes through
    `core.engine.equipe.meilleure_affectation`, a *greedy* per-slot
    assignment, so adding one genuinely-adequate candidat can reshuffle
    who fills which slot enough to make the greedy total look worse
    even though the candidat plainly fixes the flagged gap — measured
    on the real dataset, gains as low as -2 (1-100 scale) for candidats
    that did clear their besoin's bar. That made ~94% of prospection
    attempts find "no viable candidate" even though one was right there
    (see config/ia_gestion.json -> profil_cible._note and
    docs/ia-gestion.md's mercato section for the before/after counts).
    Kept as an OR rather than a replacement, so a clear whole-squad
    upgrade that doesn't happen to clear this specific besoin's bar
    still gets through; among candidates that qualify either way, the
    one with the highest `utilite()` wins (best overall fit).
    """
    candidats_tries = pool_par_poste.get(besoin.poste)
    if not candidats_tries:
        return None

    cible = besoin.niveau_attendu
    taille = cfg.ia.mercato.taille_shortlist
    notes = [note for note, _ in candidats_tries]
    centre = bisect_left(notes, cible)
    fenetre = taille * 3
    voisinage = candidats_tries[max(0, centre - fenetre) : centre + fenetre]

    candidats = [j for _, j in voisinage if j.club_id != club.id and j.id not in cibles_visees]
    candidats.sort(key=lambda j: abs(note_globale(j, cfg.attributs) - cible))
    shortlist = candidats[:taille]

    meilleur, meilleur_score = None, None
    for candidat in shortlist:
        gain = utilite(candidat, club, effectif, monde.date, cfg, sans=sans_actuel)
        comble_le_besoin = note_globale(candidat, cfg.attributs) >= besoin.niveau_attendu
        if not comble_le_besoin and gain <= 0:
            continue
        if meilleur is None or gain > meilleur_score:
            meilleur, meilleur_score = candidat, gain
    return meilleur


def _peut_se_permettre(
    club: Club, montant: int, salaire: int, effectif: list[Joueur], cfg: Config,
    montant_reserve: int = 0, salaire_reserve: int = 0,
) -> bool:
    if montant + montant_reserve > club.budget_transfert:
        return False
    if not cfg.ia.garde_fous.plafond_salarial_strict:
        return True
    return masse_salariale_actuelle(effectif) + salaire + salaire_reserve <= club.masse_salariale_max


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
