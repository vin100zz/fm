import { api } from "../api.js";
import { echappe, tableauTriable } from "../composants.js";

const LIBELLES_EVENEMENT = {
  but: "⚽ But",
  tir: "Tir",
  arret: "Arrêt",
  carton: "🟨 Carton",
  blessure: "🩹 Blessure",
  remplacement: "🔁 Remplacement",
};

export async function renderDetail(conteneur, id) {
  const match = await api.match(id);

  conteneur.innerHTML = `
    <h1>${echappe(match.domicile_nom)} ${match.buts_dom} - ${match.buts_ext} ${echappe(match.exterieur_nom)}</h1>
    <p>${echappe(match.competition_nom)} · Journée ${match.journee} · ${match.date}</p>

    <div class="carte">
      <table>
        <thead><tr><th></th><th>${echappe(match.domicile_nom)}</th><th>${echappe(match.exterieur_nom)}</th></tr></thead>
        <tbody>
          ${ligneStat("Tirs", match.stats_dom.tirs, match.stats_ext.tirs)}
          ${ligneStat("xG", match.stats_dom.xg, match.stats_ext.xg)}
          ${ligneStat("Possession", match.stats_dom.possession_pct + " %", match.stats_ext.possession_pct + " %")}
          ${ligneStat("Corners", match.stats_dom.corners, match.stats_ext.corners)}
          ${ligneStat("Cartons jaunes", match.stats_dom.cartons_jaunes, match.stats_ext.cartons_jaunes)}
          ${ligneStat("Cartons rouges", match.stats_dom.cartons_rouges, match.stats_ext.cartons_rouges)}
        </tbody>
      </table>
    </div>

    <div style="display:flex; gap:24px; flex-wrap:wrap;">
      <div style="flex:1; min-width:280px;">
        <h2>Compositions</h2>
        <h3>${echappe(match.domicile_nom)}</h3>
        <div id="comp-dom"></div>
        <h3>${echappe(match.exterieur_nom)}</h3>
        <div id="comp-ext"></div>
      </div>
      <div style="flex:2; min-width:320px;">
        <h2>Fil du match</h2>
        <div id="fil-match"></div>
      </div>
    </div>
  `;

  const colonnesComposition = [
    { cle: "poste", libelle: "Poste" },
    { cle: "nom", libelle: "Nom", format: (_, l) => `${echappe(l.prenom)} ${echappe(l.nom)}` },
    { cle: "note", libelle: "Note" },
  ];
  tableauTriable(conteneur.querySelector("#comp-dom"), colonnesComposition, match.composition_dom, { triInitial: "note", sensInitial: true });
  tableauTriable(conteneur.querySelector("#comp-ext"), colonnesComposition, match.composition_ext, { triInitial: "note", sensInitial: true });

  conteneur.querySelector("#fil-match").innerHTML = match.evenements
    .map((e) => {
      const libelle = LIBELLES_EVENEMENT[e.type] || e.type;
      const acteurs = e.joueur_secondaire_nom ? `${echappe(e.joueur_nom)} (${echappe(e.joueur_secondaire_nom)})` : echappe(e.joueur_nom);
      return `<div class="evenement-ligne"><strong>${e.minute}'</strong> — ${libelle} : ${acteurs}${e.detail ? ` <em>(${echappe(e.detail)})</em>` : ""}</div>`;
    })
    .join("");
}

function ligneStat(libelle, valeurDom, valeurExt) {
  return `<tr><td>${libelle}</td><td>${valeurDom ?? "—"}</td><td>${valeurExt ?? "—"}</td></tr>`;
}
