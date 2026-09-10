import pytest

from core.config import Config
from core.domain.geometrie import Couloir, Zone
from core.domain.poste import Poste
from core.engine.equipe import PositionOnze
from core.engine.implication import construire_tables_implication
from core.engine.notes_zones import calculer_notes_equipe, facteur_densite, multiplicateur_moral, note_zone
from tests.unit.world.fabriques_domaine import des_attributs, un_joueur


class TestFacteurDensite:
    def test_a_la_reference_le_facteur_vaut_un(self, cfg: Config) -> None:
        assert facteur_densite(cfg.moteur.densite.reference, cfg.moteur.densite) == pytest.approx(1.0)

    def test_croissant_avec_la_densite(self, cfg: Config) -> None:
        bas = facteur_densite(1.0, cfg.moteur.densite)
        haut = facteur_densite(5.0, cfg.moteur.densite)
        assert haut > bas


class TestMultiplicateurMoral:
    def test_au_centre_de_la_plage_vaut_un(self, cfg: Config) -> None:
        centre = (cfg.etats.moral.min + cfg.etats.moral.max) / 2
        assert multiplicateur_moral(centre, cfg.etats.moral) == pytest.approx(1.0)

    def test_au_maximum_vaut_un_plus_amplitude(self, cfg: Config) -> None:
        resultat = multiplicateur_moral(cfg.etats.moral.max, cfg.etats.moral)
        assert resultat == pytest.approx(1.0 + cfg.etats.moral.amplitude_effet_match)

    def test_reste_dans_lamplitude_configuree(self, cfg: Config) -> None:
        for moral in (cfg.etats.moral.min, cfg.etats.moral.max):
            resultat = multiplicateur_moral(moral, cfg.etats.moral)
            assert 1.0 - cfg.etats.moral.amplitude_effet_match - 1e-9 <= resultat
            assert resultat <= 1.0 + cfg.etats.moral.amplitude_effet_match + 1e-9


def _onze_homogene(poste: Poste, n: int = 11) -> tuple[PositionOnze, ...]:
    return tuple(
        PositionOnze(poste=poste, joueur=un_joueur(id=i, poste=poste, attributs=des_attributs()))
        for i in range(n)
    )


class TestNoteZone:
    def test_onze_vide_retourne_le_plancher(self, cfg: Config) -> None:
        tables = construire_tables_implication(cfg.implications)
        resultat = note_zone((), Zone.MILIEU_HAUT, Couloir.AXE, True, "progression_attaque", tables, {}, cfg)
        assert resultat == cfg.moteur.densite.note_plancher

    def test_est_positif_pour_un_onze_pertinent(self, cfg: Config) -> None:
        onze = _onze_homogene(Poste.BU)
        tables = construire_tables_implication(cfg.implications)
        multiplicateurs = {position.joueur.id: 1.0 for position in onze}
        resultat = note_zone(onze, Zone.VERITE, Couloir.AXE, True, "occasion_attaque", tables, multiplicateurs, cfg)
        assert resultat > 0


class TestCalculerNotesEquipe:
    def test_construit_les_quatre_grilles_completes(self, cfg: Config) -> None:
        from core.engine.equipe import Equipe

        onze = _onze_homogene(Poste.MC)
        equipe = Equipe(club_id=1, force_attaque=50, force_defense=50, onze=onze, formation="4-4-2")
        tables = construire_tables_implication(cfg.implications)

        notes = calculer_notes_equipe(equipe, tables, cfg)

        for grille in (notes.progression_attaque, notes.progression_defense, notes.occasion_attaque, notes.occasion_defense):
            assert set(grille) == set(Zone)
            for zone_grille in grille.values():
                assert set(zone_grille) == set(Couloir)
