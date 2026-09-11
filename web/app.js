import { api } from "./api.js";
import * as vueClubs from "./vues/clubs.js";
import * as vueCompetitions from "./vues/competitions.js";
import * as vueJoueurs from "./vues/joueurs.js";
import * as vueMatch from "./vues/match.js";
import * as vueTransferts from "./vues/transferts.js";

const conteneur = document.getElementById("contenu");

async function majBarreTemps() {
  const etat = await api.etatMonde();
  document.getElementById("date-courante").textContent = etat.date;
  document.getElementById("saison-courante").textContent = `saison ${etat.saison}`;
  const echeances = Object.entries(etat.prochaines_echeances)
    .map(([nom, date]) => `${nom} : ${date}`)
    .join(" · ");
  document.getElementById("prochaines-echeances").textContent = echeances;

  const indicateurMercato = document.getElementById("mercato-indicateur");
  indicateurMercato.textContent = etat.mercato_ouvert ? "● Mercato ouvert" : "○ Mercato fermé";
  indicateurMercato.classList.toggle("mercato-ouvert", etat.mercato_ouvert);
  indicateurMercato.classList.toggle("mercato-ferme", !etat.mercato_ouvert);
}

function afficherJournal(journal) {
  const liste = document.getElementById("journal-liste");
  liste.innerHTML = journal
    .map((e) => `<li class="${e.type}">${e.description}</li>`)
    .join("") || "<li>Rien à signaler.</li>";
}

async function avancer(jusqu_a) {
  const boutons = document.querySelectorAll("#barre-temps button");
  boutons.forEach((b) => (b.disabled = true));
  try {
    const reponse = await api.avancer(jusqu_a);
    await majBarreTemps();
    afficherJournal(reponse.journal);
    await routerActuel();
    return true;
  } catch (erreur) {
    alert(erreur.message);
    return false;
  } finally {
    boutons.forEach((b) => (b.disabled = autoActif && b.id !== "btn-auto-avancer"));
  }
}

document.getElementById("btn-avancer-jour").addEventListener("click", () => avancer("jour"));
document.getElementById("btn-avancer-journee").addEventListener("click", () => avancer("journee"));

// Avance automatique : rejoue "avancer à la prochaine journée" en boucle
// jusqu'à ce qu'on re-clique sur le bouton (play/pause), avec une pause
// entre deux journées pour laisser le temps de lire le journal.
const DELAI_AUTO_MS = 900;
const boutonAuto = document.getElementById("btn-auto-avancer");
let autoActif = false;

function majBoutonAuto() {
  boutonAuto.textContent = autoActif ? "⏸ Pause" : "▶ Auto";
  boutonAuto.classList.toggle("actif", autoActif);
  document.getElementById("btn-avancer-jour").disabled = autoActif;
  document.getElementById("btn-avancer-journee").disabled = autoActif;
}

async function boucleAuto() {
  while (autoActif) {
    const succes = await avancer("journee");
    if (!succes) { autoActif = false; break; }
    if (!autoActif) break;
    await new Promise((resolution) => setTimeout(resolution, DELAI_AUTO_MS));
  }
  majBoutonAuto();
}

boutonAuto.addEventListener("click", () => {
  autoActif = !autoActif;
  majBoutonAuto();
  if (autoActif) boucleAuto();
});

const statutPartie = document.getElementById("statut-partie");
const champSlot = document.getElementById("slot-partie");
const selectSlots = document.getElementById("slots-existants");

function messageStatutPartie(texte) {
  statutPartie.textContent = texte;
  setTimeout(() => { if (statutPartie.textContent === texte) statutPartie.textContent = ""; }, 4000);
}

async function majListeSlots() {
  const slots = await api.slotsPartie().catch(() => []);
  const valeurActuelle = selectSlots.value;
  selectSlots.innerHTML = '<option value="">— sauvegardes —</option>' +
    slots.map((s) => `<option value="${s.slot}">${s.slot} (${s.modifie_le})</option>`).join("");
  selectSlots.value = slots.some((s) => s.slot === valeurActuelle) ? valeurActuelle : "";
}

selectSlots.addEventListener("change", () => {
  if (selectSlots.value) champSlot.value = selectSlots.value;
});

document.getElementById("btn-sauvegarder").addEventListener("click", async () => {
  const slot = champSlot.value.trim();
  if (!slot) { alert("Indique un nom de sauvegarde."); return; }
  try {
    await api.sauvegarderPartie(slot);
    messageStatutPartie(`Partie sauvegardée (${slot}).`);
    await majListeSlots();
  } catch (erreur) {
    alert(erreur.message);
  }
});

document.getElementById("btn-charger").addEventListener("click", async () => {
  const slot = champSlot.value.trim();
  if (!slot) { alert("Indique un nom de sauvegarde."); return; }
  if (!confirm(`Charger "${slot}" ? La progression non sauvegardée sera perdue.`)) return;
  try {
    await api.chargerPartie(slot);
    messageStatutPartie(`Partie chargée (${slot}).`);
    await majBarreTemps();
    afficherJournal([]);
    await routerActuel();
  } catch (erreur) {
    alert(erreur.message);
  }
});

// Petit routeur maison par ancre (docs/ui.md) — pas de dépendance externe.
const routes = [
  { motif: /^#\/clubs\/(\d+)$/, gestionnaire: (m) => vueClubs.renderDetail(conteneur, m[1]) },
  { motif: /^#\/clubs$/, gestionnaire: () => vueClubs.renderListe(conteneur) },
  { motif: /^#\/competitions\/(\d+)$/, gestionnaire: (m) => vueCompetitions.renderDetail(conteneur, m[1]) },
  { motif: /^#\/competitions$/, gestionnaire: () => vueCompetitions.renderListe(conteneur) },
  { motif: /^#\/joueurs\/(\d+)$/, gestionnaire: (m) => vueJoueurs.renderDetail(conteneur, m[1]) },
  { motif: /^#\/joueurs$/, gestionnaire: () => vueJoueurs.renderListe(conteneur) },
  { motif: /^#\/matches\/(\d+)$/, gestionnaire: (m) => vueMatch.renderDetail(conteneur, m[1]) },
  { motif: /^#\/transferts$/, gestionnaire: () => vueTransferts.renderListe(conteneur) },
];

async function routerActuel() {
  const hash = window.location.hash || "#/clubs";
  for (const route of routes) {
    const correspondance = hash.match(route.motif);
    if (correspondance) {
      conteneur.innerHTML = "<p>Chargement…</p>";
      try {
        await route.gestionnaire(correspondance);
      } catch (erreur) {
        conteneur.innerHTML = `<p class="echeance-proche">Erreur : ${erreur.message}</p>`;
      }
      return;
    }
  }
  conteneur.innerHTML = "<p>Page introuvable.</p>";
}

window.addEventListener("hashchange", routerActuel);

async function demarrer() {
  await majBarreTemps();
  await majListeSlots();
  try {
    afficherJournal(await api.journal());
  } catch {
    afficherJournal([]);
  }
  if (!window.location.hash) window.location.hash = "#/clubs";
  await routerActuel();
}

demarrer();
