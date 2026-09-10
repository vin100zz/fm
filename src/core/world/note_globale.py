"""Overall rating: a poste-weighted composite of the 13 attributes. See
config/attributs.json -> note_globale and docs/attributs.md. Used by
valorisation and squad-strength comparisons (docs/ia-gestion.md) and,
from step 2, to rank a squad when trimming it to size at import.
"""

from core.config.modeles.attributs import ConfigAttributs
from core.domain.attributs import combinaison_ponderee
from core.domain.joueur import Joueur


def note_globale(joueur: Joueur, cfg: ConfigAttributs) -> float:
    return combinaison_ponderee(joueur.attributs, cfg.note_globale[joueur.poste.value])
