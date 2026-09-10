"""Cross-field coherence checks, run once the whole Config tree is built.

These go beyond what a per-field pydantic constraint can express: they
compare sibling fields, or even fields across different config files.
See "Contrôles de cohérence au chargement" in docs/configuration.md.
"""

import dataclasses
from typing import Any

from core.config.modeles.racine import Config
from core.domain.poste import Poste

TOLERANCE_SOMME = 1e-6


def verifier_coherence(config: Config) -> list[str]:
    erreurs: list[str] = []
    postes = _postes_canoniques(config, erreurs)
    erreurs += _verifier_geometrie_implications(config)
    erreurs += _verifier_composites(config, postes)
    erreurs += _verifier_references_attributs(config)
    erreurs += _verifier_references_postes(config, postes)
    erreurs += _verifier_formations(config, postes)
    erreurs += _verifier_distributions(config)
    erreurs += _verifier_bornes(config)
    return erreurs


def _postes_canoniques(config: Config, erreurs: list[str]) -> set[str]:
    """The set of postes is fixed by core.domain.poste.Poste (see its
    docstring); every config file that lists postes (implications,
    formations, profils, note_globale...) must agree with it.
    """
    reference = {poste.value for poste in Poste}
    impl = config.implications
    ensembles = {
        "implications.vertical_attaque": set(impl.vertical_attaque),
        "implications.vertical_defense": set(impl.vertical_defense),
        "implications.lateral": set(impl.lateral),
    }
    for nom, ensemble in ensembles.items():
        erreurs += _comparer_postes(nom, ensemble, reference)
    return reference


def _verifier_geometrie_implications(config: Config) -> list[str]:
    impl = config.implications
    n_zones = len(impl.zones)
    n_couloirs = len(impl.couloirs)
    erreurs: list[str] = []
    for poste, vecteur in impl.vertical_attaque.items():
        if len(vecteur) != n_zones:
            erreurs.append(
                f"implications.vertical_attaque.{poste}: {len(vecteur)} "
                f"valeurs, attendu {n_zones} (nb de zones)"
            )
    for poste, vecteur in impl.vertical_defense.items():
        if len(vecteur) != n_zones:
            erreurs.append(
                f"implications.vertical_defense.{poste}: {len(vecteur)} "
                f"valeurs, attendu {n_zones} (nb de zones)"
            )
    for poste, vecteur in impl.lateral.items():
        if len(vecteur) != n_couloirs:
            erreurs.append(
                f"implications.lateral.{poste}: {len(vecteur)} valeurs, "
                f"attendu {n_couloirs} (nb de couloirs)"
            )
    return erreurs


def _somme_vaut_un(nom: str, valeurs: Any) -> list[str]:
    total = sum(valeurs)
    if abs(total - 1.0) > TOLERANCE_SOMME:
        return [f"{nom}: la somme des poids vaut {total}, attendu 1.0"]
    return []


def _verifier_composites(config: Config, postes: set[str]) -> list[str]:
    erreurs: list[str] = []
    for nom, poids in config.attributs.composites.items():
        erreurs += _somme_vaut_un(f"attributs.composites.{nom}", poids.values())
    for poste, poids in config.attributs.note_globale.items():
        erreurs += _somme_vaut_un(f"attributs.note_globale.{poste}", poids.values())
    erreurs += _comparer_postes(
        "attributs.note_globale", set(config.attributs.note_globale), postes
    )
    return erreurs


def _attributs_canoniques(config: Config) -> set[str]:
    liste = config.attributs.liste
    return set(liste.techniques) | set(liste.mentaux) | set(liste.physiques) | set(liste.gardien)


def _verifier_references_attributs(config: Config) -> list[str]:
    attributs = _attributs_canoniques(config)
    erreurs: list[str] = []

    def verifier_dict(nom: str, poids: dict[str, float], cles_ignorees: set[str] = frozenset()) -> None:
        for attribut in poids:
            if attribut in cles_ignorees:
                continue
            if attribut not in attributs:
                erreurs.append(f"{nom}: attribut inconnu '{attribut}'")

    for nom, poids in config.attributs.composites.items():
        verifier_dict(f"attributs.composites.{nom}", poids)
    for poste, poids in config.attributs.note_globale.items():
        verifier_dict(f"attributs.note_globale.{poste}", poids)
    for poste, decalages in config.attributs.profils_generation.profils.items():
        verifier_dict(f"attributs.profils_generation.profils.{poste}", decalages, {"_autres"})
    verifier_dict(
        "demographie.progression.poids_declin_par_attribut",
        config.demographie.progression.poids_declin_par_attribut,
    )
    return erreurs


def _comparer_postes(nom: str, trouves: set[str], attendus: set[str]) -> list[str]:
    erreurs = [f"{nom}: poste inconnu '{poste}'" for poste in sorted(trouves - attendus)]
    erreurs += [f"{nom}: poste manquant '{poste}'" for poste in sorted(attendus - trouves)]
    return erreurs


def _verifier_references_postes(config: Config, postes: set[str]) -> list[str]:
    erreurs: list[str] = []
    erreurs += _comparer_postes(
        "attributs.profils_generation.profils",
        set(config.attributs.profils_generation.profils),
        postes,
    )
    erreurs += _comparer_postes(
        "ia.profil_cible.effectif_par_poste",
        set(config.ia.profil_cible.effectif_par_poste),
        postes,
    )
    erreurs += _comparer_postes(
        "ia.valorisation.rarete_poste", set(config.ia.valorisation.rarete_poste), postes
    )
    erreurs += _comparer_postes(
        "demographie.cible_postes", set(config.demographie.cible_postes), postes
    )
    return erreurs


def _verifier_formations(config: Config, postes: set[str]) -> list[str]:
    erreurs: list[str] = []
    for nom, liste_postes in config.formations.formations.items():
        if len(liste_postes) != 11:
            erreurs.append(
                f"formations.formations.{nom}: {len(liste_postes)} postes, attendu 11"
            )
        for poste in liste_postes:
            if poste not in postes:
                erreurs.append(f"formations.formations.{nom}: poste inconnu '{poste}'")
    return erreurs


def _verifier_distributions(config: Config) -> list[str]:
    erreurs: list[str] = []
    erreurs += _somme_vaut_un("demographie.cible_postes", config.demographie.cible_postes.values())
    erreurs += _somme_vaut_un(
        "etats.blessures.gravites",
        [gravite.part for gravite in config.etats.blessures.gravites],
    )
    return erreurs


def _verifier_borne_incluse(nom: str, mini: float, valeur: float, maxi: float) -> list[str]:
    if not (mini <= valeur <= maxi):
        return [f"{nom}: valeur {valeur} hors de [{mini}, {maxi}]"]
    return []


def _verifier_bornes(config: Config) -> list[str]:
    erreurs: list[str] = []
    _parcourir_bornes(config, "config", erreurs)
    erreurs += _verifier_borne_incluse(
        "formations.hauteur_bloc",
        config.formations.hauteur_bloc.min,
        config.formations.hauteur_bloc.defaut,
        config.formations.hauteur_bloc.max,
    )
    erreurs += _verifier_borne_incluse(
        "etats.forme", config.etats.forme.min, config.etats.forme.initiale, config.etats.forme.max
    )
    erreurs += _verifier_borne_incluse(
        "etats.moral", config.etats.moral.min, config.etats.moral.initial, config.etats.moral.max
    )
    return erreurs


def _parcourir_bornes(valeur: Any, chemin: str, erreurs: list[str]) -> None:
    """Recursively find every dataclass carrying sibling `min`/`max`
    fields and check they are ordered. Generic on purpose: a new Plage
    added anywhere in the config tree is checked without new code here.
    """
    if dataclasses.is_dataclass(valeur) and not isinstance(valeur, type):
        champs = {champ.name: getattr(valeur, champ.name) for champ in dataclasses.fields(valeur)}
        mini, maxi = champs.get("min"), champs.get("max")
        if isinstance(mini, (int, float)) and isinstance(maxi, (int, float)) and mini > maxi:
            erreurs.append(f"{chemin}: min ({mini}) > max ({maxi})")
        for nom_champ, sous_valeur in champs.items():
            _parcourir_bornes(sous_valeur, f"{chemin}.{nom_champ}", erreurs)
    elif isinstance(valeur, dict):
        for cle, sous_valeur in valeur.items():
            _parcourir_bornes(sous_valeur, f"{chemin}.{cle}", erreurs)
    elif isinstance(valeur, (list, tuple)):
        for index, sous_valeur in enumerate(valeur):
            _parcourir_bornes(sous_valeur, f"{chemin}[{index}]", erreurs)
