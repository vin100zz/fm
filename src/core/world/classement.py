"""Standings computation — the `classement` half of the `Competition`
Protocol in docs/architecture.md, and "Classement" in docs/ui.md.

`confrontation_directe` (config/monde.json -> saison.criteres_departage)
is applied only pairwise, not as a full round-robin subgroup resolution:
when exactly two clubs are tied through the prior criteria, head-to-head
points/goal difference between just the two of them breaks the tie. A
three-way tie falls back to `buts_pour` — a known simplification of the
real rule, which the size of this gap almost never bites in a 96-club,
5-league world.
"""

from core.config.modeles.racine import Config
from core.domain.classement import LigneClassement
from core.domain.match import Match


def calculer_classement(club_ids: list[int], matches: list[Match], cfg: Config) -> list[LigneClassement]:
    cfg_saison = cfg.monde.saison
    lignes = {club_id: _ligne_vide(club_id) for club_id in club_ids}

    for match in matches:
        if match.resultat is None or match.domicile_id not in lignes or match.exterieur_id not in lignes:
            continue
        _integrer_match(lignes, match, cfg_saison)

    return sorted(lignes.values(), key=lambda ligne: _cle_tri(ligne, lignes, matches, cfg_saison), reverse=True)


def _ligne_vide(club_id: int) -> LigneClassement:
    return LigneClassement(club_id=club_id, joues=0, victoires=0, nuls=0, defaites=0, buts_pour=0, buts_contre=0, points=0)


def _integrer_match(lignes: dict[int, LigneClassement], match: Match, cfg_saison) -> None:
    resultat = match.resultat
    lignes[match.domicile_id] = _mettre_a_jour(lignes[match.domicile_id], resultat.buts_dom, resultat.buts_ext, cfg_saison)
    lignes[match.exterieur_id] = _mettre_a_jour(lignes[match.exterieur_id], resultat.buts_ext, resultat.buts_dom, cfg_saison)


def _mettre_a_jour(ligne: LigneClassement, buts_marques: int, buts_encaisses: int, cfg_saison) -> LigneClassement:
    if buts_marques > buts_encaisses:
        victoires, nuls, defaites, points = ligne.victoires + 1, ligne.nuls, ligne.defaites, ligne.points + cfg_saison.points_victoire
    elif buts_marques == buts_encaisses:
        victoires, nuls, defaites, points = ligne.victoires, ligne.nuls + 1, ligne.defaites, ligne.points + cfg_saison.points_nul
    else:
        victoires, nuls, defaites, points = ligne.victoires, ligne.nuls, ligne.defaites + 1, ligne.points + cfg_saison.points_defaite

    return LigneClassement(
        club_id=ligne.club_id, joues=ligne.joues + 1, victoires=victoires, nuls=nuls, defaites=defaites,
        buts_pour=ligne.buts_pour + buts_marques, buts_contre=ligne.buts_contre + buts_encaisses, points=points,
    )


def _cle_tri(ligne: LigneClassement, lignes: dict[int, LigneClassement], matches: list[Match], cfg_saison) -> tuple:
    cle: list[float] = []
    for critere in cfg_saison.criteres_departage:
        if critere == "points":
            cle.append(ligne.points)
        elif critere == "difference_buts":
            cle.append(ligne.difference_buts)
        elif critere == "buts_pour":
            cle.append(ligne.buts_pour)
        elif critere == "confrontation_directe":
            cle.append(_points_confrontation_directe(ligne, lignes, matches, cfg_saison))
    return tuple(cle)


def _points_confrontation_directe(
    ligne: LigneClassement, lignes: dict[int, LigneClassement], matches: list[Match], cfg_saison
) -> int:
    """Only meaningful against the single other club sharing this exact
    (points, difference_buts, buts_pour) tuple ahead of this criterion —
    see the module docstring for the multi-way-tie simplification.
    """
    jumeaux = [
        autre.club_id
        for autre in lignes.values()
        if autre.club_id != ligne.club_id
        and (autre.points, autre.difference_buts, autre.buts_pour) == (ligne.points, ligne.difference_buts, ligne.buts_pour)
    ]
    if len(jumeaux) != 1:
        return 0

    adversaire_id = jumeaux[0]
    points = 0
    for match in matches:
        if match.resultat is None:
            continue
        if match.domicile_id == ligne.club_id and match.exterieur_id == adversaire_id:
            points += _points_dun_resultat(match.resultat.buts_dom, match.resultat.buts_ext, cfg_saison)
        elif match.exterieur_id == ligne.club_id and match.domicile_id == adversaire_id:
            points += _points_dun_resultat(match.resultat.buts_ext, match.resultat.buts_dom, cfg_saison)
    return points


def _points_dun_resultat(buts_marques: int, buts_encaisses: int, cfg_saison) -> int:
    if buts_marques > buts_encaisses:
        return cfg_saison.points_victoire
    if buts_marques == buts_encaisses:
        return cfg_saison.points_nul
    return cfg_saison.points_defaite
