"""Deep merge for override folders and stripping of "_note" comment keys."""

from typing import Any


def retirer_notes(valeur: Any) -> Any:
    """Recursively drop "_note" keys, ignored comments in config JSON files."""
    if isinstance(valeur, dict):
        return {
            cle: retirer_notes(sous_valeur)
            for cle, sous_valeur in valeur.items()
            if cle != "_note"
        }
    if isinstance(valeur, list):
        return [retirer_notes(element) for element in valeur]
    return valeur


def fusionner(base: dict[str, Any], surcharge: dict[str, Any]) -> dict[str, Any]:
    """Merge `surcharge` onto `base`, recursively for nested dicts.

    A key present in `surcharge` replaces the one in `base`; lists and
    scalars are replaced wholesale, never concatenated or merged element
    by element, so an override file can shrink a list.
    """
    resultat = dict(base)
    for cle, valeur in surcharge.items():
        existant = resultat.get(cle)
        if isinstance(existant, dict) and isinstance(valeur, dict):
            resultat[cle] = fusionner(existant, valeur)
        else:
            resultat[cle] = valeur
    return resultat
