"""The 10 postes. Kept as code (not config) because the engine, the
attribute profiles and the implication matrices all key off this exact
set — see docs/attributs.md and docs/moteur-match.md. The config
coherence checks (core/config/coherence.py) verify every config file
that lists postes agrees with this set.
"""

from enum import Enum


class Poste(Enum):
    GB = "GB"
    DC = "DC"
    DL = "DL"
    DR = "DR"
    MDC = "MDC"
    MC = "MC"
    MOC = "MOC"
    AILG = "AILG"
    AILD = "AILD"
    BU = "BU"
