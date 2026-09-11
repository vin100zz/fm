import { api } from "../api.js";
import { echappe, tableauTriable } from "../composants.js";

export async function renderListe(conteneur) {
  const etatPage = { page: 1, saison: "" };
  const etatMonde = await api.etatMonde();

  conteneur.innerHTML = `
    <h1>Transferts</h1>
    <div class="filtres">
      <select id="f-saison">
        <option value="">Toutes les saisons</option>
        ${Array.from({ length: etatMonde.saison }, (_, i) => i + 1)
          .reverse()
          .map((s) => `<option value="${s}">Saison ${s}</option>`)
          .join("")}
      </select>
    </div>
    <div id="resultats"></div>
    <div class="pagination">
      <button id="page-precedente">◀</button>
      <span id="page-info"></span>
      <button id="page-suivante">▶</button>
    </div>
  `;

  const resultats = conteneur.querySelector("#resultats");
  const infoPage = conteneur.querySelector("#page-info");

  async function charger() {
    const page = await api.transferts({ saison: etatPage.saison, page: etatPage.page });
    if (!page.items.length) {
      resultats.innerHTML = "<p>Aucun transfert.</p>";
      infoPage.textContent = "";
      return;
    }
    const colonnes = [
      { cle: "date", libelle: "Date" },
      { cle: "joueur_nom", libelle: "Joueur", format: (v, l) => `<a href="#/joueurs/${l.joueur_id}">${echappe(v)}</a>` },
      {
        cle: "club_source_nom", libelle: "Origine",
        format: (v, l) => (l.club_source_id ? `<a href="#/clubs/${l.club_source_id}">${echappe(v)}</a>` : "—"),
      },
      {
        cle: "club_cible_nom", libelle: "Destination",
        format: (v, l) => (l.club_cible_id ? `<a href="#/clubs/${l.club_cible_id}">${echappe(v)}</a>` : "—"),
      },
      { cle: "montant", libelle: "Montant", format: (v) => `${v.toLocaleString("fr-FR")} €` },
      { cle: "saison", libelle: "Saison" },
    ];
    tableauTriable(resultats, colonnes, page.items, { triInitial: "date", sensInitial: true });
    const dernierePage = Math.max(1, Math.ceil(page.total / page.taille_page));
    infoPage.textContent = `Page ${page.page} / ${dernierePage} (${page.total} transferts)`;
  }

  conteneur.querySelector("#f-saison").addEventListener("change", (e) => { etatPage.saison = e.target.value; etatPage.page = 1; charger(); });
  conteneur.querySelector("#page-precedente").addEventListener("click", () => { etatPage.page = Math.max(1, etatPage.page - 1); charger(); });
  conteneur.querySelector("#page-suivante").addEventListener("click", () => { etatPage.page += 1; charger(); });

  await charger();
}
