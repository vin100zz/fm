"""Recurring club cash flow: wages paid out and billetterie/merchandising
income received, every month. See "Budgets" in docs/ia-gestion.md.

The other half of the economy — the annual, classement-based competition
prize (`core.ai.budgets.prime_classement`) — is paid separately at season
rollover (`core/world/saison.py`), since it needs a season's actual final
table rather than anything known on an arbitrary day here.
"""

from core.ai.budgets import depense_mensuelle_salaires, masse_salariale_actuelle, revenu_mensuel
from core.config.modeles.racine import Config
from core.domain.club import StatutClub
from core.domain.historique import MouvementFinancier, TypeMouvementFinancier
from core.domain.joueur import Joueur
from core.domain.monde import Monde


def appliquer_flux_mensuel(monde: Monde, cfg: Config) -> None:
    if monde.date.jour != 1:
        return

    effectifs_par_club: dict[int, list[Joueur]] = {}
    for joueur in monde.joueurs.values():
        if joueur.club_id is not None:
            effectifs_par_club.setdefault(joueur.club_id, []).append(joueur)

    for club in monde.clubs.values():
        if club.statut is not StatutClub.ACTIF:
            continue
        effectif = effectifs_par_club.get(club.id, [])
        # revenu_mensuel prend la masse salariale REELLEMENT payee, pas
        # club.masse_salariale_max (un plafond fixe) : un effectif plus
        # petit gagne aussi moins, plutot qu'un plafond qui paie plein
        # pot quel que soit le vrai effectif — voir le docstring de
        # revenu_mensuel (2026-09-12, deuxieme passe).
        revenu = revenu_mensuel(masse_salariale_actuelle(effectif), cfg)
        depense = depense_mensuelle_salaires(effectif, cfg)
        # Both derived from the *same* masse_salariale_actuelle, so flux
        # is structurally >= 0 (revenu_mensuel inverts part_revenus_salaires,
        # always leaving a positive margin over the wages it was computed
        # from) — wages alone can no longer put a club in debt. A club can
        # still show a real deficit only from overspending on transfers,
        # which _peut_se_permettre (core/world/mercato.py) already guards
        # against before any offer is made.
        club.solde += revenu - depense
        club.budget_transfert += revenu - depense
        # Revenu et depense sont journalises separement (pas juste le flux
        # net) : demande explicite de l'utilisateur pour l'historique
        # financier de l'onglet Budget ("tous les revenus et toutes les
        # depenses").
        monde.historique.mouvements_financiers.append(
            MouvementFinancier(TypeMouvementFinancier.REVENU_MENSUEL, monde.date, club.id, revenu, monde.saison)
        )
        monde.historique.mouvements_financiers.append(
            MouvementFinancier(TypeMouvementFinancier.SALAIRES, monde.date, club.id, -depense, monde.saison)
        )
