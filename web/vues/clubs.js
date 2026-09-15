import { api } from "../api.js";
import { echappe, formeBadges, posteBadge, tableauTriable } from "../composants.js";

export async function renderListe(conteneur) {
  const etat = { page: 1, statut: "", recherche: "", competition: "", tri: "nom" };
  const competitions = await api.competitions();

  conteneur.innerHTML = `
    <h1>Clubs</h1>
    <div class="filtres">
      <input type="search" id="f-recherche" placeholder="Rechercher un club…" />
      <select id="f-statut">
        <option value="">Tous les statuts</option>
        <option value="actif">Actifs</option>
        <option value="dormant">Dormants</option>
      </select>
      <select id="f-competition">
        <option value="">Toutes les compétitions</option>
        ${competitions.map((c) => `<option value="${c.id}">${echappe(c.nom)}</option>`).join("")}
      </select>
      <select id="f-tri">
        <option value="nom">Trier par nom</option>
        <option value="reputation">Trier par réputation</option>
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
    const page = await api.clubs({
      statut: etat.statut, recherche: etat.recherche, competition: etat.competition, tri: etat.tri, page: etat.page,
    });
    const colonnes = [
      { cle: "nom", libelle: "Club" },
      { cle: "pays", libelle: "Pays" },
      { cle: "statut", libelle: "Statut" },
      { cle: "reputation", libelle: "Réputation" },
      { cle: "nb_joueurs_sous_contrat", libelle: "Sous contrat" },
      { cle: "masse_salariale", libelle: "Masse salariale/sem.", format: (v) => `${v.toLocaleString("fr-FR")} €` },
      { cle: "budget_transfert", libelle: "Budget transferts", format: (v) => `${v.toLocaleString("fr-FR")} €` },
    ];
    tableauTriable(resultats, colonnes, page.items, {
      onClicLigne: (id) => (window.location.hash = `#/clubs/${id}`),
    });
    const dernierePage = Math.max(1, Math.ceil(page.total / page.taille_page));
    infoPage.textContent = `Page ${page.page} / ${dernierePage} (${page.total} clubs)`;
  }

  conteneur.querySelector("#f-recherche").addEventListener("input", (e) => { etat.recherche = e.target.value; etat.page = 1; charger(); });
  conteneur.querySelector("#f-statut").addEventListener("change", (e) => { etat.statut = e.target.value; etat.page = 1; charger(); });
  conteneur.querySelector("#f-competition").addEventListener("change", (e) => { etat.competition = e.target.value; etat.page = 1; charger(); });
  conteneur.querySelector("#f-tri").addEventListener("change", (e) => { etat.tri = e.target.value; charger(); });
  conteneur.querySelector("#page-precedente").addEventListener("click", () => { etat.page = Math.max(1, etat.page - 1); charger(); });
  conteneur.querySelector("#page-suivante").addEventListener("click", () => { etat.page += 1; charger(); });

  await charger();
}

export async function renderDetail(conteneur, id) {
  const club = await api.club(id);

  conteneur.innerHTML = `
    <h1>${echappe(club.nom)} <span class="statut-dormant">${club.statut === "dormant" ? "(club dormant)" : ""}</span></h1>
    <p>${echappe(club.pays)} · Réputation ${club.reputation}
      ${club.classement_actuel ? ` · ${club.classement_actuel}e au classement` : ""}
      ${club.forme_recente.length ? ` · Forme : ${formeBadges(club.forme_recente)}` : ""}
    </p>
    <p>
      ${club.nb_joueurs_sous_contrat} joueur${club.nb_joueurs_sous_contrat > 1 ? "s" : ""} sous contrat ·
      Masse salariale : ${club.masse_salariale.toLocaleString("fr-FR")} €/sem. ·
      Budget transferts : ${club.budget_transfert.toLocaleString("fr-FR")} €
    </p>
    ${club.statut === "dormant" ? '<p class="statut-dormant">Club dormant : pas de classement, de calendrier ni de statistiques de saison.</p>' : ""}
    <div class="onglets">
      <button data-onglet="effectif" class="actif">Effectif</button>
      <button data-onglet="calendrier">Calendrier</button>
      <button data-onglet="transferts">Transferts</button>
      <button data-onglet="budget">Budget</button>
    </div>
    <div id="contenu-onglet"></div>
  `;

  const contenuOnglet = conteneur.querySelector("#contenu-onglet");

  async function afficherEffectif() {
    const effectif = await api.effectifClub(id);
    const colonnes = [
      { cle: "poste", libelle: "Poste", format: (v) => posteBadge(v) },
      { cle: "nom", libelle: "Nom", format: (_, l) => `${echappe(l.prenom)} ${echappe(l.nom)}` },
      { cle: "age", libelle: "Âge" },
      { cle: "niveau", libelle: "Note" },
      { cle: "salaire_hebdo", libelle: "Salaire/sem." },
      { cle: "date_fin_contrat", libelle: "Fin de contrat", classe: (l) => (l.echeance_proche ? "echeance-proche" : "") },
    ];
    tableauTriable(contenuOnglet, colonnes, effectif, {
      triInitial: "poste",
      onClicLigne: (jid) => (window.location.hash = `#/joueurs/${jid}`),
    });
  }

  async function afficherCalendrier() {
    const calendrier = await api.calendrierClub(id);
    const colonnes = [
      { cle: "journee", libelle: "J." },
      { cle: "date", libelle: "Date" },
      { cle: "domicile_nom", libelle: "Domicile" },
      { cle: "exterieur_nom", libelle: "Extérieur" },
      {
        cle: "joue", libelle: "Score",
        format: (joue, l) => (joue ? `${l.buts_dom} - ${l.buts_ext}` : "à venir"),
      },
    ];
    tableauTriable(contenuOnglet, colonnes, calendrier, {
      triInitial: "journee",
      onClicLigne: (mid) => (window.location.hash = `#/matches/${mid}`),
    });
  }

  async function afficherTransferts() {
    contenuOnglet.innerHTML = `
      <h2>Transferts</h2>
      <div id="transferts-payants"></div>
      <h2>Départs libres (fin de contrat)</h2>
      <div id="departs-libres"></div>
      <h2>Retraites</h2>
      <div id="retraites"></div>
      <h2>Promotions du centre de formation</h2>
      <div id="promotions"></div>
    `;

    const transferts = await api.transfertsClub(id);
    const conteneurTransferts = contenuOnglet.querySelector("#transferts-payants");
    if (!transferts.length) {
      conteneurTransferts.innerHTML = "<p>Aucun transfert cette saison.</p>";
    } else {
      const colonnes = [
        { cle: "date", libelle: "Date" },
        { cle: "sens", libelle: "Sens", format: (v) => (v === "arrivee" ? "↘ Arrivée" : "↗ Départ") },
        { cle: "joueur_nom", libelle: "Joueur", format: (v, l) => `<a href="#/joueurs/${l.joueur_id}">${echappe(v)}</a>` },
        {
          cle: "club_source_nom", libelle: "De",
          format: (v, l) => (l.club_source_id ? `<a href="#/clubs/${l.club_source_id}">${echappe(v)}</a>` : "—"),
        },
        {
          cle: "club_cible_nom", libelle: "Vers",
          format: (v, l) => (l.club_cible_id ? `<a href="#/clubs/${l.club_cible_id}">${echappe(v)}</a>` : "—"),
        },
        { cle: "montant", libelle: "Montant", format: (v) => `${v.toLocaleString("fr-FR")} €` },
      ];
      tableauTriable(conteneurTransferts, colonnes, transferts, { triInitial: "date", sensInitial: true });
    }

    await afficherMouvementsEffectif("fin_contrat", "#departs-libres", "Aucun départ libre.");
    await afficherMouvementsEffectif("retraite", "#retraites", "Aucune retraite.");
    await afficherMouvementsEffectif("promotion", "#promotions", "Aucune promotion du centre de formation.");
  }

  async function afficherMouvementsEffectif(type, selecteur, messageVide) {
    const mouvements = await api.mouvementsEffectifClub(id, type);
    const conteneurSection = contenuOnglet.querySelector(selecteur);
    if (!conteneurSection) return;
    if (!mouvements.length) {
      conteneurSection.innerHTML = `<p>${messageVide}</p>`;
      return;
    }
    const colonnes = [
      { cle: "date", libelle: "Date" },
      {
        // Un joueur a la retraite a quitte Monde.joueurs (core/world/
        // demographie/cycle_annuel.py) : pas de fiche a lier vers un id
        // qui n'existe plus, contrairement a fin_contrat/promotion.
        cle: "joueur_nom", libelle: "Joueur",
        format: (v, l) => (l.type === "retraite" ? echappe(v) : `<a href="#/joueurs/${l.joueur_id}">${echappe(v)}</a>`),
      },
      { cle: "saison", libelle: "Saison" },
    ];
    tableauTriable(conteneurSection, colonnes, mouvements, { triInitial: "date", sensInitial: true });
  }

  async function afficherBudget() {
    contenuOnglet.innerHTML = `
      <div class="carte">
        <strong>Budget transferts :</strong> ${club.budget_transfert.toLocaleString("fr-FR")} €<br />
        <strong>Masse salariale :</strong> ${club.masse_salariale.toLocaleString("fr-FR")} €/sem.
          (plafond ${club.masse_salariale_max.toLocaleString("fr-FR")} €/sem.)<br />
        <strong>Solde :</strong> ${club.solde.toLocaleString("fr-FR")} €
      </div>
      <h2>Historique financier</h2>
      <div id="historique-financier"></div>
    `;

    const historique = await api.historiqueFinancierClub(id);
    const conteneurHistorique = contenuOnglet.querySelector("#historique-financier");
    if (!historique.length) {
      conteneurHistorique.innerHTML = "<p>Aucun mouvement financier enregistré.</p>";
      return;
    }
    const colonnes = [
      { cle: "date", libelle: "Date" },
      { cle: "description", libelle: "Description" },
      {
        cle: "montant", libelle: "Montant",
        format: (v) => `<span class="${v >= 0 ? "montant-positif" : "montant-negatif"}">${v.toLocaleString("fr-FR")} €</span>`,
      },
      { cle: "saison", libelle: "Saison" },
    ];
    tableauTriable(conteneurHistorique, colonnes, historique, { triInitial: "date", sensInitial: true });
  }

  conteneur.querySelectorAll(".onglets button").forEach((btn) => {
    btn.addEventListener("click", () => {
      conteneur.querySelectorAll(".onglets button").forEach((b) => b.classList.remove("actif"));
      btn.classList.add("actif");
      if (btn.dataset.onglet === "effectif") afficherEffectif();
      else if (btn.dataset.onglet === "calendrier") afficherCalendrier();
      else if (btn.dataset.onglet === "budget") afficherBudget();
      else afficherTransferts();
    });
  });

  await afficherEffectif();
}
