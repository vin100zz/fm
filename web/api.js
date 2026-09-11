// Thin fetch wrapper — le serveur est la seule source de vérité,
// rien n'est mis en cache côté client (docs/ui.md).

async function requete(chemin, options) {
  const reponse = await fetch(chemin, options);
  if (!reponse.ok) {
    const corps = await reponse.json().catch(() => ({}));
    throw new Error(corps.detail || `Erreur ${reponse.status}`);
  }
  return reponse.json();
}

function avecParametres(chemin, params) {
  const url = new URL(chemin, window.location.origin);
  for (const [cle, valeur] of Object.entries(params || {})) {
    if (valeur !== undefined && valeur !== null && valeur !== "") {
      url.searchParams.set(cle, valeur);
    }
  }
  return url.pathname + url.search;
}

export const api = {
  etatMonde: () => requete("/api/monde/etat"),
  avancer: (jusqu_a) => requete("/api/monde/avancer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jusqu_a }),
  }),
  journal: () => requete("/api/monde/journal"),

  clubs: (params) => requete(avecParametres("/api/clubs", params)),
  club: (id) => requete(`/api/clubs/${id}`),
  effectifClub: (id) => requete(`/api/clubs/${id}/effectif`),
  calendrierClub: (id) => requete(`/api/clubs/${id}/calendrier`),
  transfertsClub: (id) => requete(`/api/clubs/${id}/transferts`),

  competitions: () => requete("/api/competitions"),
  classement: (id) => requete(`/api/competitions/${id}/classement`),
  calendrierCompetition: (id, journee) => requete(avecParametres(`/api/competitions/${id}/calendrier`, { journee })),
  historiqueCompetition: (id) => requete(`/api/competitions/${id}/historique`),

  joueurs: (params) => requete(avecParametres("/api/joueurs", params)),
  joueur: (id) => requete(`/api/joueurs/${id}`),

  match: (id) => requete(`/api/matches/${id}`),

  sauvegarderPartie: (slot) => requete("/api/partie/sauvegarder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slot }),
  }),
  chargerPartie: (slot) => requete("/api/partie/charger", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slot }),
  }),
  slotsPartie: () => requete("/api/partie/slots"),
};
