"""Generate a full Attributs set around a target level for a poste,
using the position profiles from config/attributs.json — the same
mechanism docs/progression-demographie.md specifies for regens. Reused
by the v0 data-import synthesis (core/world/import/construction.py) and,
from step 8 onward, by regen generation itself.
"""

from random import Random

from core.config.modeles.attributs import ConfigAttributs
from core.domain.attributs import NOMS_ATTRIBUTS, Attributs
from core.domain.poste import Poste


def generer_attributs_depuis_niveau(
    niveau: float, poste: Poste, cfg: ConfigAttributs, rng: Random
) -> Attributs:
    profil = cfg.profils_generation.profils.get(poste.value, {})
    decalage_autres = profil.get("_autres", 0.0)
    ecart_type = cfg.profils_generation.bruit_ecart_type

    valeurs: dict[str, int] = {}
    for nom in NOMS_ATTRIBUTS:
        decalage = profil.get(nom, decalage_autres)
        brut = niveau + decalage + rng.gauss(0.0, ecart_type)
        valeurs[nom] = round(min(max(brut, cfg.bornes.min), cfg.bornes.max))

    return Attributs(**valeurs)
