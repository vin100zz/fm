from core.config.fusion import fusionner, retirer_notes


def test_retirer_notes_supprime_les_cles_note_recursivement() -> None:
    donnees = {
        "_note": "commentaire",
        "a": 1,
        "b": {"_note": "autre commentaire", "c": 2},
        "d": [{"_note": "dans une liste"}, {"e": 3}],
    }

    resultat = retirer_notes(donnees)

    assert resultat == {"a": 1, "b": {"c": 2}, "d": [{}, {"e": 3}]}


def test_retirer_notes_garde_les_autres_cles_commencant_par_underscore() -> None:
    donnees = {"GB": {"reflexes": 15, "_autres": -25}}

    assert retirer_notes(donnees) == {"GB": {"reflexes": 15, "_autres": -25}}


def test_fusionner_remplace_une_cle_scalaire() -> None:
    base = {"transitions": {"k_prog": 0.055, "k_occ": 0.048}}
    surcharge = {"transitions": {"k_prog": 0.09}}

    resultat = fusionner(base, surcharge)

    assert resultat == {"transitions": {"k_prog": 0.09, "k_occ": 0.048}}


def test_fusionner_remplace_une_liste_entierement() -> None:
    base = {"criteres": ["points", "difference_buts"]}
    surcharge = {"criteres": ["points"]}

    resultat = fusionner(base, surcharge)

    assert resultat == {"criteres": ["points"]}


def test_fusionner_ajoute_une_cle_absente_de_la_base() -> None:
    base = {"a": {"x": 1}}
    surcharge = {"a": {"y": 2}}

    resultat = fusionner(base, surcharge)

    assert resultat == {"a": {"x": 1, "y": 2}}
