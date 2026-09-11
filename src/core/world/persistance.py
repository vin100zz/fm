"""Save/load a game — CLAUDE.md: "sauvegarde de partie en JSON gzippé,
pas de base de données."

Generic, type-hint-driven (de)serialization rather than a bespoke
function per domain type: every persisted object is already a plain
dataclass (CLAUDE.md's own convention — `dataclass(slots=True)` for
entities), so walking `dataclasses.fields` to serialize and
`typing.get_type_hints` to reconstruct handles the whole `Monde` graph,
including nested dataclasses, enums, `dict`/`list`/`tuple` and
`X | None`. A new domain field then needs no change here — exactly the
"local change" CLAUDE.md's extensibility goal asks for.

The RNG stream is saved alongside `Monde`, not reseeded from
`Monde.graine` on load: `Random.getstate()` is itself JSON-serializable
once its internal tuple is listified, and restoring it via `setstate()`
resumes the exact same sequence a save mid-stream would otherwise
interrupt (reseeding from `graine` would replay from the start of that
seed instead — reproducible, but not a true continuation). `graine` on
`Monde` still records what a *fresh* replay was seeded with, per
CLAUDE.md.
"""

import gzip
import json
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from random import Random
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints

import core.domain as domaine
from core.domain.monde import Monde

# Resout les references avant (ex. Competition.calendrier: list["Journee"])
# que les imports sous TYPE_CHECKING laissent absentes de l'espace de
# noms d'execution des modules domain/*.py.
_TYPES_DOMAINE = {nom: getattr(domaine, nom) for nom in domaine.__all__}


@lru_cache(maxsize=None)
def _indices_type(cls: type) -> dict:
    # get_type_hints() fait une vraie resolution d'annotations (pas
    # gratuit) — mise en cache par classe, pas par instance : sans ca,
    # charger 32 000 Joueur revient a le refaire 32 000 fois pour le
    # meme type.
    return get_type_hints(cls, localns=_TYPES_DOMAINE)


@dataclass(frozen=True, slots=True)
class InfoSauvegarde:
    slot: str
    taille_octets: int
    modifie_le: float  # timestamp Unix, cote appelant de formater


_NIVEAU_COMPRESSION = 1  # vitesse plutot que taille : un save doit rester instantane (~30000 joueurs)


def sauvegarder(monde: Monde, rng: Random, chemin: Path) -> None:
    enveloppe = {"monde": _vers_json(monde), "rng_etat": _etat_rng_vers_json(rng)}
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(gzip.compress(json.dumps(enveloppe).encode("utf-8"), compresslevel=_NIVEAU_COMPRESSION))


def charger(chemin: Path) -> tuple[Monde, Random]:
    enveloppe = json.loads(gzip.decompress(chemin.read_bytes()))
    monde = _depuis_json(enveloppe["monde"], Monde)
    rng = _rng_depuis_json(enveloppe["rng_etat"])
    return monde, rng


def lister_sauvegardes(dossier: Path) -> list[InfoSauvegarde]:
    if not dossier.exists():
        return []
    infos = []
    for chemin in sorted(dossier.glob("*.json.gz")):
        stat = chemin.stat()
        infos.append(InfoSauvegarde(slot=chemin.name.removesuffix(".json.gz"), taille_octets=stat.st_size, modifie_le=stat.st_mtime))
    return infos


def _etat_rng_vers_json(rng: Random) -> list:
    version, etat_interne, gauss_suivant = rng.getstate()
    return [version, list(etat_interne), gauss_suivant]


def _rng_depuis_json(etat: list) -> Random:
    version, etat_interne, gauss_suivant = etat
    rng = Random()
    rng.setstate((version, tuple(etat_interne), gauss_suivant))
    return rng


@lru_cache(maxsize=None)
def _noms_champs(cls: type) -> tuple[str, ...]:
    return tuple(champ.name for champ in fields(cls))


def _vers_json(valeur: Any) -> Any:
    if isinstance(valeur, Enum):
        return valeur.value
    if is_dataclass(valeur):
        return {nom: _vers_json(getattr(valeur, nom)) for nom in _noms_champs(type(valeur))}
    if isinstance(valeur, dict):
        return {_cle_vers_json(cle): _vers_json(v) for cle, v in valeur.items()}
    if isinstance(valeur, (list, tuple)):
        return [_vers_json(v) for v in valeur]
    return valeur  # int, float, str, bool, None : deja du JSON natif


def _cle_vers_json(cle: Any) -> str:
    return cle.value if isinstance(cle, Enum) else str(cle)


def _depuis_json(valeur: Any, type_cible: Any) -> Any:
    origine = get_origin(type_cible)

    if origine is Union or origine is UnionType:
        sous_types = [t for t in get_args(type_cible) if t is not type(None)]
        return None if valeur is None else _depuis_json(valeur, sous_types[0])

    if origine is list:
        (sous_type,) = get_args(type_cible)
        return [_depuis_json(v, sous_type) for v in valeur]

    if origine is tuple:
        sous_types = get_args(type_cible)
        if len(sous_types) == 2 and sous_types[1] is Ellipsis:
            return tuple(_depuis_json(v, sous_types[0]) for v in valeur)
        return tuple(_depuis_json(v, t) for v, t in zip(valeur, sous_types))

    if origine is dict:
        cle_type, valeur_type = get_args(type_cible)
        return {_cle_depuis_json(cle, cle_type): _depuis_json(v, valeur_type) for cle, v in valeur.items()}

    if is_dataclass(type_cible):
        indices = _indices_type(type_cible)
        return type_cible(**{nom: _depuis_json(valeur[nom], t) for nom, t in indices.items()})

    if isinstance(type_cible, type) and issubclass(type_cible, Enum):
        return type_cible(valeur)

    return valeur  # int, float, str, bool : deja le bon type depuis JSON


def _cle_depuis_json(cle: str, type_cible: Any) -> Any:
    if isinstance(type_cible, type) and issubclass(type_cible, Enum):
        return type_cible(cle)
    if type_cible is int:
        return int(cle)
    return cle
