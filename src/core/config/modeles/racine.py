from pydantic.dataclasses import dataclass

from core.config.modeles.attributs import ConfigAttributs
from core.config.modeles.benchmarks import ConfigBenchmarks
from core.config.modeles.commun import STRICT
from core.config.modeles.demographie import ConfigDemographie
from core.config.modeles.etats import ConfigEtats
from core.config.modeles.formations import ConfigFormations
from core.config.modeles.ia_gestion import ConfigIA
from core.config.modeles.implications import ConfigImplications
from core.config.modeles.import_donnees import ConfigImport
from core.config.modeles.moteur_match import ConfigMoteur
from core.config.modeles.monde import ConfigMonde


@dataclass(frozen=True, slots=True, config=STRICT)
class Config:
    monde: ConfigMonde
    attributs: ConfigAttributs
    implications: ConfigImplications
    formations: ConfigFormations
    moteur: ConfigMoteur
    etats: ConfigEtats
    ia: ConfigIA
    demographie: ConfigDemographie
    benchmarks: ConfigBenchmarks
    import_donnees: ConfigImport
