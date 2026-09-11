import { api } from "../api.js";
import { barreAttribut, echappe, posteBadge, tableauTriable } from "../composants.js";

const POSTES = ["GB", "DC", "DL", "DR", "MDC", "MC", "MOC", "AILG", "AILD", "BU"];

export async function renderListe(conteneur) {
  const etat = { page: 1, poste: "", age_min: "", age_max: "", niveau_min: "", nation: "", statut_club: "", tri: "niveau" };

  conteneur.innerHTML = `
    <h1>Recherche de joueurs</h1>
    <div class="filtres">
      <select id="f-poste"><option value="">Tous postes</option>${POSTES.map((p) => `<option value="${p}">${p}</option>`).join("")}</select>
      <input type="number" id="f-age-min" placeholder="Âge min" style="width:80px" />
      <input type="number" id="f-age-max" placeholder="Âge max" style="width:80px" />
      <input type="number" id="f-niveau-min" placeholder="Niveau min" style="width:90px" />
      <input type="text" id="f-nation" placeholder="Nationalité" />
      <select id="f-statut">
        <option value="">Actifs et dormants</option>
        <option value="actif">Clubs actifs</option>
        <option value="dormant">Clubs dormants</option>
      </select>
      <select id="f-tri">
        <option value="niveau">Trier par niveau</option>
        <option value="age">Trier par âge</option>
        <option value="nom">Trier par nom</option>
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
    const page = await api.joueurs({
      poste: etat.poste, age_min: etat.age_min, age_max: etat.age_max, niveau_min: etat.niveau_min,
      nation: etat.nation, statut_club: etat.statut_club, tri: etat.tri, page: etat.page,
    });
    const colonnes = [
      { cle: "poste", libelle: "Poste", format: (v) => posteBadge(v) },
      { cle: "nom", libelle: "Nom", format: (_, l) => `${echappe(l.prenom)} ${echappe(l.nom)}` },
      { cle: "age", libelle: "Âge" },
      { cle: "niveau", libelle: "Niveau" },
      { cle: "nationalite", libelle: "Nation" },
      { cle: "club_nom", libelle: "Club", format: (v, l) => v ? `${echappe(v)}${l.statut_club === "dormant" ? " (dormant)" : ""}` : "Libre" },
      { cle: "date_fin_contrat", libelle: "Fin de contrat", classe: (l) => (l.echeance_proche ? "echeance-proche" : "") },
    ];
    tableauTriable(resultats, colonnes, page.items, {
      onClicLigne: (id) => (window.location.hash = `#/joueurs/${id}`),
    });
    const dernierePage = Math.max(1, Math.ceil(page.total / page.taille_page));
    infoPage.textContent = `Page ${page.page} / ${dernierePage} (${page.total} joueurs)`;
  }

  const brancherFiltre = (id, cle) =>
    conteneur.querySelector(id).addEventListener("input", (e) => { etat[cle] = e.target.value; etat.page = 1; charger(); });
  brancherFiltre("#f-poste", "poste");
  brancherFiltre("#f-age-min", "age_min");
  brancherFiltre("#f-age-max", "age_max");
  brancherFiltre("#f-niveau-min", "niveau_min");
  brancherFiltre("#f-nation", "nation");
  conteneur.querySelector("#f-statut").addEventListener("change", (e) => { etat.statut_club = e.target.value; etat.page = 1; charger(); });
  conteneur.querySelector("#f-tri").addEventListener("change", (e) => { etat.tri = e.target.value; charger(); });
  conteneur.querySelector("#page-precedente").addEventListener("click", () => { etat.page = Math.max(1, etat.page - 1); charger(); });
  conteneur.querySelector("#page-suivante").addEventListener("click", () => { etat.page += 1; charger(); });

  await charger();
}

export async function renderDetail(conteneur, id) {
  const joueur = await api.joueur(id);
  const etat = joueur.etat;

  const familles = Object.entries(joueur.attributs)
    .map(
      ([famille, attrs]) => `
      <div class="carte">
        <h3>${echappe(famille)}</h3>
        ${Object.entries(attrs).map(([nom, valeur]) => `<div class="ligne-attribut"><span class="nom-attribut">${echappe(nom)}</span>${barreAttribut(valeur)}</div>`).join("")}
      </div>`
    )
    .join("");

  conteneur.innerHTML = `
    <h1>${echappe(joueur.prenom)} ${echappe(joueur.nom)} ${posteBadge(joueur.poste)}</h1>
    <p>${echappe(joueur.nationalite)} · ${joueur.age} ans (né le ${joueur.date_naissance})</p>

    <div class="carte">
      <strong>Potentiel estimé :</strong> entre ${joueur.potentiel_estime.min} et ${joueur.potentiel_estime.max}
      <br /><strong>Niveau actuel :</strong> ${joueur.niveau}
      <br /><strong>Valeur de marché estimée :</strong> ${joueur.valeur_estimee.toLocaleString("fr-FR")} €
    </div>

    <div class="carte">
      <strong>Club :</strong> ${joueur.club_nom ? echappe(joueur.club_nom) : "Libre"}
      ${joueur.salaire_hebdo ? `<br /><strong>Salaire hebdomadaire :</strong> ${joueur.salaire_hebdo.toLocaleString("fr-FR")} €` : ""}
      ${joueur.date_fin_contrat ? `<br /><strong>Fin de contrat :</strong> ${joueur.date_fin_contrat}` : ""}
    </div>

    <div class="carte">
      <strong>État :</strong>
      ${etat.blesse ? `<span class="echeance-proche">Blessé (${etat.jours_indisponibilite_restants} j restants)</span>` : "Apte"}
      ${etat.suspendu ? ` · <span class="echeance-proche">Suspendu (${etat.matches_suspension_restants} match(s))</span>` : ""}
      <br />Fatigue : ${etat.fatigue} · Forme : ${etat.forme} · Moral : ${etat.moral}
    </div>

    <h2>Caractéristiques</h2>
    <div style="display:flex; flex-wrap:wrap; gap:12px;">${familles}</div>
  `;
}
