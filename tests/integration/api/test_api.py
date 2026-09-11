"""End-to-end checks against the real ~32k-player world — see
tests/integration/api/conftest.py. These are invariant checks, not
exact-value assertions (docs/architecture.md's own rule for
tests/integration/): the world state after a `/avancer` call from an
earlier test in this session is not predictable to the day.
"""

import pytest
from fastapi.testclient import TestClient

from api.routes_partie import DOSSIER_SAUVEGARDES

SLOT_TEST = "test_integration_ephemere"


@pytest.fixture
def slot_ephemere():
    chemin = DOSSIER_SAUVEGARDES / f"{SLOT_TEST}.json.gz"
    yield SLOT_TEST
    chemin.unlink(missing_ok=True)


def test_etat_renvoie_une_date_et_une_saison(client: TestClient) -> None:
    reponse = client.get("/api/monde/etat")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["saison"] == 1
    assert corps["date"]


def test_lister_clubs_actifs_seulement(client: TestClient) -> None:
    reponse = client.get("/api/clubs", params={"statut": "actif"})
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["total"] == 96  # 5 championnats, ~96 clubs actifs (CLAUDE.md)
    assert all(club["statut"] == "actif" for club in corps["items"])


def test_lister_clubs_recherche_par_nom(client: TestClient) -> None:
    reponse = client.get("/api/clubs", params={"statut": "actif", "recherche": "Paris SG"})
    corps = reponse.json()
    assert corps["total"] == 1
    assert corps["items"][0]["nom"] == "Paris SG"


def test_detail_club_actif_a_un_classement(client: TestClient) -> None:
    club_id = client.get("/api/clubs", params={"statut": "actif", "recherche": "Paris SG"}).json()["items"][0]["id"]
    reponse = client.get(f"/api/clubs/{club_id}")
    assert reponse.status_code == 200
    assert reponse.json()["classement_actuel"] is not None


def test_detail_club_inconnu_404(client: TestClient) -> None:
    assert client.get("/api/clubs/999999999999").status_code == 404


def test_effectif_club_appartient_bien_au_club(client: TestClient) -> None:
    club_id = client.get("/api/clubs", params={"statut": "actif", "recherche": "Paris SG"}).json()["items"][0]["id"]
    effectif = client.get(f"/api/clubs/{club_id}/effectif").json()
    assert len(effectif) > 0
    assert all(joueur["club_id"] == club_id for joueur in effectif)


def test_calendrier_club_contient_uniquement_ses_matches(client: TestClient) -> None:
    club_id = client.get("/api/clubs", params={"statut": "actif", "recherche": "Paris SG"}).json()["items"][0]["id"]
    calendrier = client.get(f"/api/clubs/{club_id}/calendrier").json()
    assert len(calendrier) == 34  # Ligue 1 : 18 clubs, aller-retour
    assert all(club_id in (m["domicile_id"], m["exterieur_id"]) for m in calendrier)


def test_lister_competitions_renvoie_les_5_championnats(client: TestClient) -> None:
    competitions = client.get("/api/competitions").json()
    assert {c["nom"] for c in competitions} == {"Ligue 1", "La Liga", "Serie A", "Premier League", "Bundesliga"}


def test_classement_trie_par_points_decroissant(client: TestClient) -> None:
    competition_id = next(c["id"] for c in client.get("/api/competitions").json() if c["nom"] == "Ligue 1")
    classement = client.get(f"/api/competitions/{competition_id}/classement").json()
    assert len(classement) == 18
    points = [ligne["points"] for ligne in classement]
    assert points == sorted(points, reverse=True)


def test_historique_competition_vide_avant_toute_fin_de_saison(client: TestClient) -> None:
    # Une saison reelle dure 34-38 journees : pas question de la jouer
    # entierement ici. On verifie juste que l'endpoint repond, vide.
    competition_id = next(c["id"] for c in client.get("/api/competitions").json() if c["nom"] == "Ligue 1")
    reponse = client.get(f"/api/competitions/{competition_id}/historique")
    assert reponse.status_code == 200
    assert reponse.json() == []


def test_competition_inconnue_404(client: TestClient) -> None:
    assert client.get("/api/competitions/999999/classement").status_code == 404


def test_recherche_joueurs_respecte_les_filtres(client: TestClient) -> None:
    reponse = client.get("/api/joueurs", params={"poste": "BU", "age_max": 23, "statut_club": "actif"})
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["total"] > 0
    assert all(j["poste"] == "BU" and j["age"] <= 23 for j in corps["items"])


def test_recherche_joueurs_poste_invalide_400(client: TestClient) -> None:
    assert client.get("/api/joueurs", params={"poste": "PAS_UN_POSTE"}).status_code == 400


def test_detail_joueur_et_fourchette_de_potentiel(client: TestClient) -> None:
    joueur_id = client.get("/api/joueurs", params={"statut_club": "actif"}).json()["items"][0]["id"]
    reponse = client.get(f"/api/joueurs/{joueur_id}")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["potentiel_estime"]["min"] <= corps["potentiel_estime"]["max"]


def test_joueur_inconnu_404(client: TestClient) -> None:
    assert client.get("/api/joueurs/999999999999").status_code == 404


def test_avancer_un_jour_avance_la_date(client: TestClient) -> None:
    date_avant = client.get("/api/monde/etat").json()["date"]
    reponse = client.post("/api/monde/avancer", json={"jusqu_a": "jour"})
    assert reponse.status_code == 200
    assert reponse.json()["date"] != date_avant


def test_avancer_jusqua_journee_produit_un_match_consultable(client: TestClient) -> None:
    reponse = client.post("/api/monde/avancer", json={"jusqu_a": "journee"})
    journal = reponse.json()["journal"]
    resultats = [e for e in journal if e["type"] == "resultat"]
    assert resultats

    match = client.get(f"/api/matches/{resultats[0]['match_id']}").json()
    assert len(match["composition_dom"]) == 11
    assert len(match["composition_ext"]) == 11
    assert match["buts_dom"] >= 0 and match["buts_ext"] >= 0


def test_transferts_club_reflete_les_mouvements_reels(client: TestClient) -> None:
    # A ce point, plusieurs avancer_un_jour/journee ont deja tourne
    # pendant la fenetre d'ete (10/08 en fait partie) : le mercato a eu
    # l'occasion de produire de vrais transferts sur les 96 clubs actifs.
    club_id = client.get("/api/clubs", params={"statut": "actif", "recherche": "Paris SG"}).json()["items"][0]["id"]
    reponse = client.get(f"/api/clubs/{club_id}/transferts")
    assert reponse.status_code == 200
    for transfert in reponse.json():
        assert transfert["sens"] in ("arrivee", "depart")
        assert club_id in (transfert["club_source_id"], transfert["club_cible_id"])
        assert transfert["montant"] > 0


def test_transferts_club_filtre_par_saison_inexistante(client: TestClient) -> None:
    club_id = client.get("/api/clubs", params={"statut": "actif", "recherche": "Paris SG"}).json()["items"][0]["id"]
    reponse = client.get(f"/api/clubs/{club_id}/transferts", params={"saison": 9999})
    assert reponse.status_code == 200
    assert reponse.json() == []


def test_transferts_club_inconnu_404(client: TestClient) -> None:
    assert client.get("/api/clubs/999999999999/transferts").status_code == 404


def test_match_inconnu_404(client: TestClient) -> None:
    assert client.get("/api/matches/999999999999").status_code == 404


def test_sauvegarder_puis_charger_restaure_l_etat(client: TestClient, slot_ephemere: str) -> None:
    etat_avant = client.get("/api/monde/etat").json()

    reponse = client.post("/api/partie/sauvegarder", json={"slot": slot_ephemere})
    assert reponse.status_code == 200

    # Fait avancer le monde pour de vrai, pour verifier que /charger revient
    # bien en arriere, pas seulement que la date affichee ne bouge pas.
    client.post("/api/monde/avancer", json={"jusqu_a": "journee"})
    etat_avance = client.get("/api/monde/etat").json()
    assert etat_avance["date"] != etat_avant["date"]

    reponse = client.post("/api/partie/charger", json={"slot": slot_ephemere})
    assert reponse.status_code == 200

    etat_restaure = client.get("/api/monde/etat").json()
    assert etat_restaure == etat_avant


def test_charger_slot_inconnu_404(client: TestClient) -> None:
    reponse = client.post("/api/partie/charger", json={"slot": "ce_slot_n_existe_pas"})
    assert reponse.status_code == 404


def test_lister_slots_contient_la_sauvegarde(client: TestClient, slot_ephemere: str) -> None:
    client.post("/api/partie/sauvegarder", json={"slot": slot_ephemere})

    slots = client.get("/api/partie/slots").json()
    assert slot_ephemere in {s["slot"] for s in slots}
