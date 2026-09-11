// Petits composants partagés entre les vues — pas de framework
// (docs/ui.md : "un framework n'apporterait rien ici").

export function posteBadge(poste) {
  return `<span class="poste-badge poste-${poste}">${poste}</span>`;
}

export function formeBadges(lettres) {
  return lettres.map((l) => `<span class="forme-lettre forme-${l}">${l}</span>`).join("");
}

export function echappe(texte) {
  const div = document.createElement("div");
  div.textContent = texte ?? "";
  return div.innerHTML;
}

// colonnes: [{cle, libelle, format?(valeur, ligne) -> string, triable?: bool}]
// Sans `options.triInitial`, les lignes s'affichent dans l'ordre reçu
// (déjà trié côté serveur pour les listes paginées) — cliquer un
// en-tête trie alors en croissant, comme la convention habituelle.
export function tableauTriable(conteneur, colonnes, lignes, options = {}) {
  let colonneTri = options.triInitial ?? null;
  let sensDescendant = options.sensInitial ?? false;
  let lignesActuelles = lignes;

  function rendre() {
    const triees = colonneTri
      ? [...lignesActuelles].sort((a, b) => {
          const va = a[colonneTri];
          const vb = b[colonneTri];
          const cmp = typeof va === "string" ? va.localeCompare(vb) : va - vb;
          return sensDescendant ? -cmp : cmp;
        })
      : lignesActuelles;

    const enTetes = colonnes
      .map((col) => {
        const fleche = col.cle === colonneTri ? (sensDescendant ? " ▼" : " ▲") : "";
        return `<th data-cle="${col.cle}">${col.libelle}${fleche}</th>`;
      })
      .join("");

    const rangees = triees
      .map((ligne) => {
        const cellules = colonnes
          .map((col) => `<td class="${col.classe ? col.classe(ligne) : ""}">${col.format ? col.format(ligne[col.cle], ligne) : echappe(ligne[col.cle])}</td>`)
          .join("");
        const clic = options.onClicLigne ? ` data-clickable="1"` : "";
        const id = ligne[options.cleId || "id"];
        return `<tr${clic} data-id="${id ?? ""}">${cellules}</tr>`;
      })
      .join("");

    conteneur.innerHTML = `<table><thead><tr>${enTetes}</tr></thead><tbody>${rangees}</tbody></table>`;

    conteneur.querySelectorAll("th[data-cle]").forEach((th) => {
      th.addEventListener("click", () => {
        const cle = th.dataset.cle;
        if (cle === colonneTri) sensDescendant = !sensDescendant;
        else { colonneTri = cle; sensDescendant = false; }
        rendre();
      });
    });

    if (options.onClicLigne) {
      conteneur.querySelectorAll("tbody tr").forEach((tr) => {
        tr.style.cursor = "pointer";
        tr.addEventListener("click", () => options.onClicLigne(tr.dataset.id));
      });
    }
  }

  rendre();
  return {
    majLignes(nouvellesLignes) {
      lignesActuelles = nouvellesLignes;
      rendre();
    },
  };
}

export function barreAttribut(valeur) {
  const pct = Math.max(0, Math.min(100, valeur));
  return `<div class="attribut-barre-fond"><div class="attribut-barre" style="width:${pct}%"></div></div> ${valeur}`;
}
