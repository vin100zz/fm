import { api } from "../api.js";
import { echappe, tableauTriable } from "../composants.js";

export async function renderListe(conteneur) {
  const competitions = await api.competitions();
  conteneur.innerHTML = `
    <h1>Compétitions</h1>
    <ul>
      ${competitions
        .map((c) => `<li><a href="#/competitions/${c.id}">${echappe(c.nom)}</a> — ${echappe(c.pays)}, ${c.nb_clubs} clubs</li>`)
        .join("")}
    </ul>
  `;
}

export async function renderDetail(conteneur, id) {
  const [competitions, classement] = await Promise.all([api.competitions(), api.classement(id)]);
  const competition = competitions.find((c) => String(c.id) === String(id));

  conteneur.innerHTML = `
    <h1>${echappe(competition ? competition.nom : "Compétition")}</h1>
    <div class="onglets">
      <button data-onglet="classement" class="actif">Classement</button>
      <button data-onglet="calendrier">Calendrier</button>
      <button data-onglet="historique">Historique</button>
    </div>
    <div id="contenu-onglet"></div>
  `;

  const contenuOnglet = conteneur.querySelector("#contenu-onglet");

  function afficherClassement() {
    const colonnes = [
      { cle: "rang", libelle: "#" },
      { cle: "club_nom", libelle: "Club" },
      { cle: "joues", libelle: "J" },
      { cle: "victoires", libelle: "V" },
      { cle: "nuls", libelle: "N" },
      { cle: "defaites", libelle: "D" },
      { cle: "buts_pour", libelle: "BP" },
      { cle: "buts_contre", libelle: "BC" },
      { cle: "difference_buts", libelle: "Diff." },
      { cle: "points", libelle: "Pts" },
    ];
    tableauTriable(contenuOnglet, colonnes, classement, {
      triInitial: "rang", cleId: "club_id", onClicLigne: (cid) => (window.location.hash = `#/clubs/${cid}`),
    });
  }

  async function afficherCalendrier(journee) {
    const matches = await api.calendrierCompetition(id, journee || undefined);
    contenuOnglet.innerHTML = `
      <div class="filtres">
        <label>Journée : <input type="number" id="f-journee" min="1" value="${journee || ""}" placeholder="toutes" /></label>
      </div>
      <div id="tableau-calendrier"></div>
    `;
    contenuOnglet.querySelector("#f-journee").addEventListener("change", (e) => afficherCalendrier(e.target.value));

    const colonnes = [
      { cle: "journee", libelle: "J." },
      { cle: "date", libelle: "Date" },
      { cle: "domicile_nom", libelle: "Domicile" },
      { cle: "exterieur_nom", libelle: "Extérieur" },
      { cle: "joue", libelle: "Score", format: (joue, l) => (joue ? `${l.buts_dom} - ${l.buts_ext}` : "à venir") },
    ];
    tableauTriable(contenuOnglet.querySelector("#tableau-calendrier"), colonnes, matches, {
      triInitial: "journee", onClicLigne: (mid) => (window.location.hash = `#/matches/${mid}`),
    });
  }

  async function afficherHistorique() {
    const saisons = await api.historiqueCompetition(id);
    if (!saisons.length) {
      contenuOnglet.innerHTML = "<p>Aucune saison terminée pour l'instant.</p>";
      return;
    }
    contenuOnglet.innerHTML = saisons
      .map(
        (s) => `
        <div class="carte">
          <h3>Saison ${s.saison} — Champion : ${echappe(s.champion_nom)}</h3>
          <div class="tableau-historique-${s.saison}"></div>
        </div>`
      )
      .join("");
    for (const s of saisons) {
      const colonnes = [
        { cle: "rang", libelle: "#" },
        { cle: "club_nom", libelle: "Club" },
        { cle: "points", libelle: "Pts" },
        { cle: "difference_buts", libelle: "Diff." },
      ];
      tableauTriable(contenuOnglet.querySelector(`.tableau-historique-${s.saison}`), colonnes, s.classement_final, {
        triInitial: "rang", cleId: "club_id", onClicLigne: (cid) => (window.location.hash = `#/clubs/${cid}`),
      });
    }
  }

  conteneur.querySelectorAll(".onglets button").forEach((btn) => {
    btn.addEventListener("click", () => {
      conteneur.querySelectorAll(".onglets button").forEach((b) => b.classList.remove("actif"));
      btn.classList.add("actif");
      if (btn.dataset.onglet === "classement") afficherClassement();
      else if (btn.dataset.onglet === "calendrier") afficherCalendrier();
      else afficherHistorique();
    });
  });

  afficherClassement();
}
