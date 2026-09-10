"""Parse the source data's position notation (data/players.csv, column
"Position", e.g. "AM RL, ST", "D/WB L, DM") into a Poste + secondary
postes. Self-derived from the notation's grammar (no official mapping
table was available) — see docs/modele-donnees.md. Expect to refine
this once real position/attribute data replaces the v0 synthesis.

Grammar, as observed over the 250 distinct strings in the data:
  chaine   := groupe ("," groupe)*
  groupe   := roles (" " cotes)?
  roles    := ROLE ("/" ROLE)*          -- e.g. "D/WB/AM"
  cotes    := COTE+                     -- e.g. "RLC" -> R, L, C

A group with no side letters (DM, ST, GK) is inherently central/unique.
Every (role, cote) pair found, left to right, maps to a Poste; the
first one is the poste principal, the rest become postes_secondaires
at a flat default affinity (config/import.json -> postes).
"""

from core.domain.poste import Poste
from core.world.importation.erreurs import ImportInvalide

_POSTE_PAR_ROLE_COTE: dict[tuple[str, str | None], Poste] = {
    ("GK", None): Poste.GB,
    ("D", "C"): Poste.DC,
    ("D", "L"): Poste.DL,
    ("D", "R"): Poste.DR,
    ("WB", "C"): Poste.DC,
    ("WB", "L"): Poste.DL,
    ("WB", "R"): Poste.DR,
    ("DM", None): Poste.MDC,
    ("M", "C"): Poste.MC,
    ("M", "L"): Poste.AILG,
    ("M", "R"): Poste.AILD,
    ("AM", "C"): Poste.MOC,
    ("AM", "L"): Poste.AILG,
    ("AM", "R"): Poste.AILD,
    ("ST", None): Poste.BU,
    ("F", None): Poste.BU,
    ("F", "C"): Poste.BU,
}


def _paires_du_groupe(groupe: str) -> list[tuple[str, str | None]]:
    if " " in groupe:
        roles_str, cotes_str = groupe.split(" ", 1)
    else:
        roles_str, cotes_str = groupe, ""
    roles = roles_str.split("/")
    if cotes_str:
        return [(role, cote) for role in roles for cote in cotes_str]
    return [(role, None) for role in roles]


def parser_postes(
    chaine: str, affinite_secondaire: float
) -> tuple[Poste, dict[Poste, float]]:
    paires = [paire for groupe in chaine.split(",") for paire in _paires_du_groupe(groupe.strip())]

    postes: list[Poste] = []
    for paire in paires:
        poste = _POSTE_PAR_ROLE_COTE.get(paire)
        if poste is not None and poste not in postes:
            postes.append(poste)

    if not postes:
        raise ImportInvalide([f"position non reconnue: {chaine!r}"])

    principal, *secondaires = postes
    return principal, {poste: affinite_secondaire for poste in secondaires}
