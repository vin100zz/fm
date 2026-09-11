"""Squad needs: compare the real squad to a target profile derived from
reputation — see "Profil cible et besoins" in docs/ia-gestion.md.

Surplus here only means "deeper than needed at this poste" — docs also
mentions overpaid/ageing/unhappy players as surplus candidates, which
needs contract cost comparisons and moral (not implemented, see
docs/etats-joueur.md) to judge properly. Deferred rather than guessed.
"""

from core.config.modeles.racine import Config
from core.domain.besoin import Besoin, TypeBesoin
from core.domain.club import Club
from core.domain.joueur import Joueur
from core.domain.poste import Poste
from core.world.note_globale import note_globale


def niveau_cible(club: Club, cfg: Config) -> float:
    cfg_pc = cfg.ia.profil_cible
    return cfg_pc.niveau_base + cfg_pc.poids_reputation * club.reputation


def evaluer_besoins(club: Club, effectif: list[Joueur], cfg: Config) -> list[Besoin]:
    cfg_pc = cfg.ia.profil_cible
    cible = niveau_cible(club, cfg)

    par_poste: dict[Poste, list[Joueur]] = {}
    for joueur in effectif:
        par_poste.setdefault(joueur.poste, []).append(joueur)

    besoins: list[Besoin] = []
    for poste_code, profil in cfg_pc.effectif_par_poste.items():
        poste = Poste(poste_code)
        disponibles = sorted(par_poste.get(poste, []), key=lambda joueur: note_globale(joueur, cfg.attributs), reverse=True)
        rangs_attendus = (
            [cible] * profil.titulaires
            + [cible - cfg_pc.decote_rotation] * profil.rotations
            + [cible - cfg_pc.decote_doublure] * profil.doublures
        )

        for rang, niveau_attendu in enumerate(rangs_attendus):
            niveau_reel = note_globale(disponibles[rang], cfg.attributs) if rang < len(disponibles) else 0.0
            if niveau_reel < niveau_attendu:
                besoins.append(Besoin(type=TypeBesoin.MANQUE, poste=poste, urgence=niveau_attendu - niveau_reel))

        for surplus in disponibles[len(rangs_attendus):]:
            besoins.append(
                Besoin(
                    type=TypeBesoin.SURPLUS, poste=poste, urgence=note_globale(surplus, cfg.attributs),
                    joueur_id=surplus.id,
                )
            )

    besoins.sort(key=lambda besoin: besoin.urgence, reverse=True)
    return besoins


def rang_au_poste(joueur: Joueur, effectif: list[Joueur], cfg: Config) -> int:
    """0 = best-rated player at this poste in `effectif` (joueur included
    if present). Shared by core/ai/mercato.py (temps_jeu_projete,
    surplus) and core/ai/contrats.py (minutes_attendues) — both need
    "where would/does this player rank at this club".
    """
    memes_postes = sorted(
        (autre for autre in effectif if autre.poste is joueur.poste),
        key=lambda autre: note_globale(autre, cfg.attributs),
        reverse=True,
    )
    for rang, autre in enumerate(memes_postes):
        if autre.id == joueur.id:
            return rang
    # joueur absent de l'effectif : son rang hypothetique s'il rejoignait
    niveau = note_globale(joueur, cfg.attributs)
    return sum(1 for autre in memes_postes if note_globale(autre, cfg.attributs) > niveau)


def profondeur_utile(poste: Poste, cfg: Config) -> int:
    profil = cfg.ia.profil_cible.effectif_par_poste.get(poste.value)
    if profil is None:
        return 1
    return profil.titulaires + profil.rotations + profil.doublures


def projeter_temps_jeu(joueur: Joueur, effectif: list[Joueur], cfg: Config) -> float:
    """0-1: how much playing time this poste-rank realistically gets at
    this club. No exact formula in docs/ia-gestion.md ("compare le
    niveau du joueur à l'effectif d'accueil à son poste") — this ramps
    from 1.0 for a clear starter down to 0.0 once past the useful depth
    for that poste (config/ia_gestion.json -> profil_cible).
    """
    profil = cfg.ia.profil_cible.effectif_par_poste.get(joueur.poste.value)
    titulaires = profil.titulaires if profil else 1
    profondeur = profondeur_utile(joueur.poste, cfg)
    rang = rang_au_poste(joueur, effectif, cfg)

    if rang < titulaires:
        return 1.0
    if rang >= profondeur:
        return 0.0
    return 1.0 - (rang - titulaires + 1) / (profondeur - titulaires + 1)
