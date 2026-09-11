# IA de gestion

> Toutes les valeurs numériques de ce document sont dans `config/ia_gestion.json`.
> Les tableaux ci-dessous documentent les valeurs initiales ; la source de
> vérité est le JSON. Aucune constante ne doit apparaître dans le code.

En v1, **les 96 clubs sont pilotés par cette IA**. C'est elle qui produit
l'essentiel de ce que l'utilisateur observe.

## État de l'implémentation (2026-09-11)

Implémenté dans `src/core/ai/` : `valorisation.py` (§1, `valeur`,
`estimation_potentiel`), `utilite.py` (§2), `besoins.py` (§3, plus des
fonctions de profondeur d'effectif partagées avec `mercato.py`/`contrats.py`),
`budgets.py` (§4), `selection.py` (§8 et "Décision de remplacement" dans
`docs/etats-joueur.md`), `mercato.py` (§5, réponse du vendeur et score d'une
offre) et `contrats.py` (§6, satisfaction et renouvellement). `controller.py`
définit `ClubController` (le Protocol de `CLAUDE.md`, adapté aux signatures
réelles — voir sa docstring) et `AIController`, sa seule implémentation.
`core/engine/match.py::MoteurPossession.simuler` consomme
`selection.choisir_composition`/`decider_remplacement` via des paramètres
optionnels — voir "Remplacements (étape 7)" dans `docs/moteur-match.md`.

**`tour_mercato` (§5) implémenté (2026-09-11, ajouté après l'étape 9)** —
`core/world/mercato.py`, appelé depuis `core/world/saison.py::avancer_un_jour`
chaque jour où `monde.date` tombe dans une fenêtre été/hiver
(`config/monde.json -> mercato`). Bilan, shortlist, offres et résolution
simultanée pour les 96 clubs actifs, avec les négociations en cours
persistées sur `Monde.negociations` (nouveau type `Negociation`) d'un tour à
l'autre. Voir "Boucle de mercato" plus bas pour le détail (convergence en
2 tours, garde-fous de budget/masse salariale, calibration du volume —
2.88 mouvements/club/saison mesuré, ce qui reste hors périmètre — agents
libres, renouvellements).

**Toujours hors périmètre** : l'orchestration hebdomadaire des
renouvellements de contrat (§6) — la fonction `decision_renouvellement`
existe et est testée, rien ne l'appelle encore selon un calendrier (contrairement
à §5, désormais appelé depuis `avancer_un_jour`).

**Formules non données par ce document, tranchées pendant l'implémentation**
(chacune documentée dans le docstring de sa fonction) :

- `surplus(club, joueur)` (§5) : rang du joueur dans la hiérarchie de son
  poste, ramené à 0-1 par rapport à la profondeur utile du poste
  (`besoins.py::rang_au_poste`/`profondeur_utile`, réutilisé de `projeter_temps_jeu`).
- `temps_jeu_projete(joueur, club)` (§5) : même idée, en sens inverse — 1.0
  pour un titulaire clair, dégressif jusqu'à 0 au-delà de la profondeur utile.
- `ambition_sportive(club)` (§5) : réutilise
  `club.personnalite.agressivite_salariale` plutôt que d'inventer un trait
  séparé.
- `reputation_attendue(joueur)` (§6) : réutilise `note_globale(joueur)`
  directement — les deux sont sur la même échelle 1-100.
- `ego` (§6) : aucun attribut de ce nom n'existe sur `Joueur` ; approximé par
  l'écart du joueur à un niveau moyen de 50 (`contrats.py::_ego`), sur la même
  idée que la convexité en talent de `valeur()`.
- "le club renouvelle si `utilite(joueur, club)` justifie le coût sur la
  durée" (§6) : aucune formule de coût/durée n'est donnée ; tranché comme
  "utilité marginale strictement positive ET le salaire demandé ne fait pas
  dépasser le plafond salarial" (garde-fou §7 déjà strict), en réutilisant la
  masse salariale réelle de l'effectif plutôt qu'un modèle d'amortissement
  séparé.

Toute l'IA repose sur deux fonctions et une boucle de marché.

## 1. Valeur intrinsèque

Indépendante du club. Sert de référence de prix.

```python
def valeur(joueur) -> int:
    niveau = note_globale(joueur)                    # moyenne pondérée par poste
    pot = estimation_potentiel(joueur)
    base = 1.0e6 * exp(0.115 * (max(niveau, pot * 0.75) - 55))
    return int(base * courbe_age(joueur.age) * rarete_poste(joueur.poste))
```

**La convexité en talent est essentielle.** Un joueur à 90 ne vaut pas 1.2 fois
un joueur à 75, il vaut environ 5 fois plus. Sans cela, les gros clubs achètent
dix bons joueurs au lieu d'une star et le marché n'a plus de sommet.

### Courbe d'âge

| Âge | Multiplicateur |
|---|---|
| 17 – 20 | 1.45 |
| 21 – 23 | 1.35 |
| 24 – 26 | 1.15 |
| 27 – 29 | 1.00 |
| 30 – 31 | 0.70 |
| 32 – 33 | 0.42 |
| 34+ | 0.18 |

Un joueur de 19 ans à 70 vaut plus qu'un joueur de 31 ans à 75. Interpoler
linéairement entre les paliers.

### Décote de fin de contrat

```python
mois_restants = contrat.date_fin - date_courante
if mois_restants < 6:  valeur *= 0.15
elif mois_restants < 12: valeur *= 0.45
elif mois_restants < 18: valeur *= 0.75
```

C'est ce qui alimente naturellement le marché : à un an de la fin, vendre à 45 %
vaut mieux que perdre le joueur libre.

## 2. Utilité marginale

C'est elle, et non la valeur, qui déclenche les décisions.

```python
def utilite(joueur, club) -> float:
    avec = note_meilleur_onze(club.effectif + [joueur])
    sans = note_meilleur_onze(club.effectif)
    return avec - sans
```

Un club avec trois excellents gardiens tire une utilité quasi nulle d'un
quatrième. **Cette seule idée corrige l'accumulation compulsive au même poste**,
qui est le grand classique du genre.

Moduler ensuite par la personnalité du club :

```python
utilite_ajustee = utilite * (1 + 0.35 * personnalite.preference_jeunes * jeunesse(joueur))
                          * (1 + 0.30 * personnalite.appetit_risque * incertitude_potentiel(joueur))
```

## 3. Profil cible et besoins

Chaque club vise un niveau dérivé de sa réputation :

```python
def niveau_cible(club) -> float:
    return 42 + 0.48 * club.reputation
```

Profil cible par poste : nombre de titulaires, de rotations, de doublures, et
niveau attendu pour chacun.

| Rang au poste | Niveau attendu |
|---|---|
| Titulaire | niveau_cible |
| Rotation | niveau_cible − 6 |
| Doublure | niveau_cible − 14 |

La comparaison effectif réel / profil cible produit deux listes classées :

- **Manques** : postes sous-dotés, triés par écart au profil
- **Surplus** : joueurs au-delà de la profondeur nécessaire, trop payés, âgés, ou
  mécontents

Le club vend les surplus pour financer les manques.

## 4. Budgets

Deux budgets séparés, et c'est le second qui fait tout le travail.

```python
budget_transfert = revenus_saison * 0.30 + solde * 0.40 + ventes_realisees
masse_salariale_max = revenus_saison * 0.62 / 52
```

Revenus dérivés de la réputation, du classement de la saison précédente et du
pays. **Le plafond salarial est appliqué strictement** : sans lui, l'IA explose
en cinq saisons. Un club ne peut pas signer si le nouveau salaire fait dépasser
le plafond — il doit vendre d'abord.

## 5. Boucle de mercato

**Implémenté** (2026-09-11) dans `core/world/mercato.py::tour_mercato`,
appelé une fois par jour de fenêtre depuis `avancer_un_jour`
(`config/monde.json -> mercato.tours_par_jour`, actuellement 1). Suit les
trois phases ci-dessous à la lettre, avec quelques écarts pratiques :

- **Shortlist bornée, pas exhaustive** : chaque club trie les candidats au
  poste manquant par proximité à son niveau cible, ne calcule l'utilité
  marginale réelle (coûteuse — un `meilleure_affectation` par candidat) que
  sur les `taille_shortlist` plus proches, et abandonne un besoin après
  `tentatives_prospection_max` échecs plutôt que d'épuiser toute la liste.
  Sans ça, un tour sur les 96 clubs actifs prenait ~15s (mesuré) au lieu de
  ~1.2s — un club dont l'effectif est déjà saturé (proche du plafond
  d'attribut) réévaluait en vain chacun de ses besoins à chaque tour.
- **Critère d'acceptation d'un candidat, revu (2026-09-11)** : mesuré sur
  les vraies données, seulement 12 transferts sur une saison complète des
  96 clubs actifs (attendu : 2 à 7 arrivées/départs par club). Cause :
  `_meilleur_candidat` n'acceptait un candidat que si `utilite()` — le
  gain marginal du meilleur onze — était strictement positif ; or
  `utilite()` passe par `core/engine/equipe.py::meilleure_affectation`,
  une affectation **gloutonne** poste par poste, pas globalement
  optimale — ajouter un candidat qui comble pourtant clairement le
  besoin signalé peut faire glisser l'affectation gloutonne vers un
  total légèrement (parfois nettement, jusqu'à -2 points sur l'échelle
  1-100, mesuré) pire. Résultat : ~94% des tentatives de prospection ne
  trouvaient "aucun candidat viable" alors qu'un candidat adéquat était
  bien dans la liste courte. Le critère accepte désormais un candidat
  qui **dépasse directement `besoin.niveau_attendu`** (le seuil que
  `evaluer_besoins`/`evaluer_opportunites` a utilisé pour signaler le
  besoin), en plus du critère `utilite() > 0` conservé comme alternative.
  La fenêtre de recherche est aussi recentrée sur `besoin.niveau_attendu`
  plutôt que sur le niveau cible générique du club (qui ne correspondait
  pas au rang réellement visé — rotation/doublure/opportuniste ont un
  niveau attendu différent du titulaire).
- **Prospection opportuniste (2026-09-11, ajoutée)** : sans elle, un club
  qui a comblé tous ses `MANQUE` ne prospectait plus jamais pour le reste
  de la fenêtre — aucun mécanisme ne rouvrait de besoin en cours de
  saison. `core/ai/besoins.py::evaluer_opportunites` génère, pour chaque
  titulaire déjà au niveau, un besoin synthétique (même type `MANQUE`,
  même circuit d'acceptation) exigeant qu'un candidat le dépasse d'au
  moins `marge_amelioration_opportuniste` (6.0, config) — assez pour
  ignorer le bruit d'échelle, pas assez pour ne jamais se déclencher.
  Examinée après les vrais `MANQUE` (moins prioritaire), toujours bornée
  par `tentatives_prospection_max`/`negociations_actives_max`.
- **Vente proactive vers le marché extérieur (2026-09-11, ajoutée)** :
  les deux points précédents ont fait passer le nombre de candidats
  viables trouvés de 60 à 367 (mesuré, un tour) — mais 72% d'entre eux
  restaient bloqués par `masse_salariale_max`, faute de marge : un club
  n'avait jamais aucune raison de **vendre**, seulement d'acheter. Les
  besoins `SURPLUS` existaient déjà (§3) mais rien n'agissait dessus.
  `core/world/mercato.py::_demarcher_surplus` tire, à chaque tour et
  pour chaque besoin `SURPLUS`, si un club dormant démarche ce joueur
  (`clubs_dormants.probabilite_demarchage_par_tour`, 0.002 — renommée
  et calibrée par mesure directe, elle existait depuis la construction
  initiale de la boucle mais n'était jamais lue) ; en cas de succès, le
  transfert se conclut sans négociation, même simplification que
  `repondre_offre_dormant`. Résultat mesuré sur une saison complète :
  **12 → 254 transferts** (fix précédent seul : 75), soit **2.88
  mouvements par club actif** (arrivées + départs), dans la fourchette
  2-7 visée.
  **Bug trouvé en production (2026-09-11, corrigé le jour même)** : la
  destination était d'abord choisie uniformément au hasard parmi les
  clubs dormants sans vérifier son `budget_transfert` — repéré par
  l'utilisateur (un club de 800 places au stade "achetant" un joueur à
  130M€). Le tirage est désormais borné aux clubs dormants dont le
  `budget_transfert` couvre le montant (`_clubs_dormants_tries_par_budget`,
  trié une fois par tour, `bisect` par montant) ; sans club assez riche
  disponible, le démarchage n'a simplement pas lieu ce tour.
- **La négociation converge en au plus 2 tours** : `repondre_offre` est une
  fonction pure du montant offert, donc ré-offrir exactement le montant
  contré reproduit le même seuil et le franchit. `facteur_offre_initiale`
  (1.15, config) est calé pour obtenir une contre-offre (pas un refus sec)
  dans la majorité des cas sans payer plein tarif d'entrée — le seuil vendeur
  le plus bas possible étant 1.10x `valeur()` (surplus maximal), toute offre
  sous 0.825x `valeur()` est refusée net, vérifié par mesure.
- **Bug trouvé en câblant cette boucle** : `repondre_offre` calculait
  `contre_montant = round(seuil)`, qui peut arrondir *en dessous* de
  `seuil` (partie décimale < 0.5) — ré-offrir ce montant échouait alors à
  nouveau contre le même seuil non arrondi, empêchant toute convergence.
  Corrigé en `math.ceil(seuil)` : une contre-offre est désormais toujours
  au moins égale au seuil qui l'a produite.
- **Garde-fous de budget** appliqués aux deux endroits où docs les
  implique sans les détailler : une offre (nouvelle ou relancée après
  contre-offre) doit tenir dans `budget_transfert` restant du club ET ne
  pas faire dépasser `masse_salariale_max` en ajoutant le salaire proposé
  à la masse salariale actuelle de l'effectif (`garde_fous.plafond_salarial_strict`,
  §7). Les offres simultanées d'un même club sur plusieurs négociations ce
  tour sont provisionnées ensemble (pas juste vérifiées une à une) pour ne
  pas dépasser le budget en cumulant plusieurs accords le même tour.
  Le transfert conclu déduit le montant du `budget_transfert` de
  l'acheteur et le crédite au `solde` du vendeur (si actif) — approximation
  du `ventes_realisees` de la formule de budget (§4), qui suppose un
  nouveau calcul de `revenus_saison` non modélisé ici.
- **Hors périmètre, documenté dans `core/world/mercato.py`** : pas
  d'agents libres (§ suivant, aucun contrat n'expire jamais) ; pas de prêt, clause libératoire, ni
  d'échange (`TransfertSec` — argent comptant seulement, voir
  `RegleTransfert` dans `docs/architecture.md`).

Deux fenêtres : été (6 semaines) et hiver (3 semaines). La fenêtre tourne par
**tours de jour**.

```
Bilan de l'effectif  →  Shortlist de cibles  →  Offre au vendeur
                                                      ↓
Transfert conclu  ←  Choix du joueur  ←  Réponse du vendeur
        (refus ou signature ailleurs → retour à la shortlist)
```

### Règle structurante

**Tous les clubs jouent le même tour avant que quoi que ce soit ne se résolve.**
Traiter les clubs séquentiellement fait que le premier de la liste rafle toutes
les meilleures cibles.

Chaque tour se déroule en trois phases distinctes :

```python
def tour_mercato(monde, rng):
    intentions = [club_evalue(c, monde, rng) for c in monde.clubs.values()]
    offres     = [c.emettre_offres(i, rng) for c, i in zip(clubs, intentions)]
    resoudre(offres, monde, rng)
```

Limiter chaque club à **3 négociations actives**. Sinon les gros clubs
pré-réservent tout le marché et bloquent les autres.

### Réponse du vendeur

```python
def repondre_offre(club, joueur, offre) -> Reponse:
    seuil = valeur(joueur) * (1.35 - 0.25 * surplus(club, joueur))
    seuil *= (1 + 0.4 * club.personnalite.patience_negociation)
    if offre >= seuil:            return ACCEPTE
    if offre >= seuil * 0.75:     return CONTRE_OFFRE(seuil)
    return REFUSE
```

### Choix du joueur

Indispensable, sinon le club le plus riche gagne toujours. C'est ce qui rend le
mercato vivant.

```python
def score_offre(joueur, club, salaire_propose) -> float:
    return (0.38 * ratio_salaire(salaire_propose, joueur)
          + 0.30 * temps_jeu_projete(joueur, club)
          + 0.22 * (club.reputation / 100)
          + 0.10 * ambition_sportive(club))
```

Ajouter un bruit gaussien d'écart-type 0.05. `temps_jeu_projete` compare le
niveau du joueur à l'effectif d'accueil à son poste — un cadre n'accepte pas
d'être doublure, même très bien payé.

### Agents libres

Un joueur en fin de contrat non renouvelé devient libre au 1er juillet. Il n'y a
pas de frais de transfert, seule la négociation salariale compte. Les clubs les
évaluent en priorité en début de fenêtre estivale.

## 6. Contrats et renouvellements

Même moteur, sans club acheteur. Évalué chaque semaine.

### Satisfaction du joueur

```python
def satisfaction(joueur, club) -> float:
    s_salaire = joueur.contrat.salaire_hebdo / salaire_attendu(joueur)
    s_jeu     = minutes_saison(joueur) / minutes_attendues(joueur)
    s_club    = club.reputation / reputation_attendue(joueur)
    return 0.40 * clamp(s_salaire, 0, 1.5) + 0.40 * clamp(s_jeu, 0, 1.5) + 0.20 * clamp(s_club, 0, 1.5)
```

`minutes_attendues` dépend du niveau du joueur relativement à son effectif : un
joueur nettement meilleur que ses concurrents s'attend à jouer.

### Décisions

- Satisfaction < 0.65 ou contrat à moins de 12 mois → ouverture d'une négociation
- Le joueur demande `valeur_salariale(joueur) * (1 + 0.15 * ego)`
- Le club renouvelle si `utilite(joueur, club)` justifie le coût sur la durée
- Sinon : mise sur liste de transfert, ou départ libre à échéance

C'est ce cycle — et non un système d'entraînement — qui produit le renouvellement
naturel des effectifs.

## 7. Garde-fous

C'est ici que les simulations amateurs meurent, généralement vers la saison 10.

| Garde-fou | Mise en œuvre |
|---|---|
| Plafond de masse salariale | strict, bloque la signature |
| Taille d'effectif 18 – 30 | force la vente au-dessus de 30, l'achat sous 18 |
| Minimum 2 gardiens, 3 recommandés | contrainte dure |
| Utilité décroissante par poste | assurée par le calcul marginal |
| Temps de jeu comme besoin du joueur | les stars quittent les bancs |
| Valorisation du potentiel | les vétérans ne restent pas hors de prix |

## 8. Sélection de la composition

Avant chaque match, `AIController.choisir_composition` :

1. Écarter blessés et suspendus
2. Choisir la formation : `club.formation_preferee`, sauf si l'effectif
   disponible ne la remplit pas — prendre alors la mieux remplie
3. Pour chaque poste, classer les disponibles par
   `composite_poste * forme * fatigue * malus_poste`
4. Appliquer la rotation : si un joueur est sous 0.65 de fatigue et qu'un
   remplaçant est à moins de 6 points de niveau, faire tourner
5. Hauteur de bloc : dérivée de l'écart de réputation avec l'adversaire et du
   fait de jouer à domicile

## 9. Validation

Suite `economie` de `docs/benchmarks.md`, 25 saisons sans interface. Cibles dans
`config/benchmarks.json`.

Si le talent se concentre ou si les salaires explosent, le problème est presque
toujours dans les garde-fous, pas dans les heuristiques.
