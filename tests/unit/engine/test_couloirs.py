from collections import Counter
from random import Random

from core.config import Config
from core.domain.geometrie import Couloir
from core.engine.couloirs import choisir_couloir, peut_changer_aile


class TestChoisirCouloir:
    def test_favorise_le_couloir_le_plus_favorable(self, cfg: Config) -> None:
        notes_attaque = {Couloir.GAUCHE: 40.0, Couloir.AXE: 40.0, Couloir.DROITE: 80.0}
        notes_defense = {Couloir.GAUCHE: 40.0, Couloir.AXE: 40.0, Couloir.DROITE: 40.0}
        rng = Random(1)

        tirages = [choisir_couloir(notes_attaque, notes_defense, cfg.moteur.couloirs, rng) for _ in range(2000)]

        compte = Counter(tirages)
        assert compte[Couloir.DROITE] > compte[Couloir.GAUCHE]
        assert compte[Couloir.DROITE] > compte[Couloir.AXE]

    def test_jamais_uniforme_meme_a_egalite_amelioree(self, cfg: Config) -> None:
        # a doit rester possible de tomber sur chaque couloir : le softmax
        # ne doit jamais degenerer en un choix toujours identique
        notes_attaque = {Couloir.GAUCHE: 50.0, Couloir.AXE: 55.0, Couloir.DROITE: 50.0}
        notes_defense = {Couloir.GAUCHE: 50.0, Couloir.AXE: 50.0, Couloir.DROITE: 50.0}
        rng = Random(2)

        tirages = {choisir_couloir(notes_attaque, notes_defense, cfg.moteur.couloirs, rng) for _ in range(500)}

        assert tirages == set(Couloir)


class TestPeutChangerAile:
    def test_couloir_voisin_reste_adjacent(self, cfg: Config) -> None:
        rng = Random(1)
        for _ in range(500):
            resultat = peut_changer_aile(Couloir.GAUCHE, 90.0, cfg.moteur.couloirs, rng)
            assert resultat in (Couloir.GAUCHE, Couloir.AXE)  # jamais directement DROITE

    def test_axe_peut_basculer_des_deux_cotes(self, cfg: Config) -> None:
        rng = Random(1)
        resultats = {peut_changer_aile(Couloir.AXE, 90.0, cfg.moteur.couloirs, rng) for _ in range(2000)}
        assert resultats == set(Couloir)
