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
2.88 mouvements/club/saison mesuré).

**Renouvellements et agents libres (§6) implémentés (2026-09-11, ajouté,
demande explicite de l'utilisateur)** — `core/world/contrats.py`,
appelé depuis `avancer_un_jour` : `renouveler_contrats` (mensuel, voir
"Contrats et renouvellements" plus bas pour pourquoi pas hebdomadaire
comme documenté) décide, pour chaque club actif et chaque joueur sous
contrat, s'il prolonge ; `decision_renouvellement` existait depuis
l'étape 7, rien ne l'appelait sur un calendrier avant ce jour.
`liberer_contrats_expires` (chaque 1er juillet) libère qui n'a pas été
renouvelé. `core/world/mercato.py` signe désormais aussi les agents
libres, sans négociation ni frais de transfert.

**Économie récurrente (§4) implémentée (2026-09-12, ajoutée, demande
explicite de l'utilisateur)** — `core/world/finances.py::appliquer_flux_mensuel`
(salaires payés / billetterie encaissée, chaque 1er du mois) et
`core/ai/budgets.py::prime_classement` (versée à la bascule de saison,
contre le classement final réel). Avant cet ajout, un club actif ne
gagnait de l'argent qu'au moment d'une vente ; les plus grands clubs
(Real Madrid, Barcelone, Man City) restaient bloqués à 7-9 joueurs après
4 saisons simulées faute de pouvoir jamais reconstituer un budget de
transfert à la hauteur de leur propre niveau cible (mesuré :
`budget_transfert` de Real Madrid à 3,7M€ quand ses propres besoins
demandaient 22-49M€ par recrue) — voir "Budgets" plus bas pour le détail.

**Chaque mouvement financier journalisé, pas seulement appliqué
(2026-09-12, ajouté, même demande, onglet Budget d'une fiche club)** :
`appliquer_flux_mensuel` et la prime de classement écrivent désormais
chacun de leur côté un `MouvementFinancier` (`core/domain/historique.py`,
nouveau) dans `Monde.historique.mouvements_financiers` — revenu et
dépense enregistrés séparément, jamais juste le flux net, pour que
l'historique financier liste "tous les revenus et toutes les dépenses"
tel que demandé. Les transferts ne sont pas dupliqués dans cette liste
(`Historique.transferts` reste leur seule source de vérité) ; `GET
/api/clubs/{id}/historique-financier` fusionne les deux à la lecture —
voir "Transferts" dans `docs/ui.md`.

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

Trois mécanismes distincts alimentent ou consomment le budget d'un club :
un capital de départ calculé une fois, un flux récurrent mensuel, et une
prime annuelle liée au classement. `budget_transfert` et `solde` évoluent
toujours ensemble (voir plus bas pourquoi deux champs existent malgré ça).

### Capital de départ (à l'import uniquement)

```python
budget_transfert = revenus_saison * 0.30 + solde * 0.40 + ventes_realisees
masse_salariale_max = revenus_saison * 0.62 / 52   # plancher, voir plus bas
```

Revenus dérivés de la réputation et du pays (`core/ai/budgets.py::calculer_revenus`,
`classement_precedent=None` à l'import — aucune saison précédente à lire).
Ce calcul n'est fait **qu'une fois**, dans
`core/world/importation/construction.py`, et sert uniquement à amorcer
`budget_transfert` (`masse_salariale_max` calculé ici n'est plus la
valeur finale, voir "Plafond salarial ancré sur les vrais salaires"
ci-dessous). **Le plafond salarial est appliqué strictement** : sans
lui, l'IA explose en cinq saisons. Un club ne peut pas signer si le
nouveau salaire fait dépasser le plafond — il doit vendre d'abord.

### Plafond salarial ancré sur les vrais salaires importés

**Corrigé 2026-09-12, demande explicite de l'utilisateur.** Le plafond
ci-dessus, dérivé uniquement de la réputation, sous-évaluait
drastiquement les très grands clubs : mesuré, Real Madrid importe
5,3M€/semaine de salaires réels contre un plafond dérivé de la
réputation à 1,03M€/semaine (x5,2). Comme `decision_renouvellement`
(§6) bloque tout renouvellement dès que la masse salariale de l'effectif
dépasse le plafond (`sous_plafond`, une porte ET, pas une des conditions
du OU), ce décalage empêchait purement et simplement Real Madrid de
renouveler qui que ce soit — les grands clubs s'effondraient à 6-9
joueurs sur 4 saisons simulées, indépendamment de tout autre correctif
(voir "Renouvellements" plus bas).

`core/world/importation/__init__.py`, juste après la construction des
joueurs (`core/ai/budgets.py::masse_salariale_max_reelle`), recalcule
donc le plafond de chaque club à partir de sa masse salariale **réellement
importée** :

```python
masse_salariale_max = max(masse_salariale_reelle_importee * 1.10, masse_salariale_max_derive_de_la_reputation)
```

Le plafond dérivé de la réputation (calculé plus haut, à l'import) sert
de **plancher**, pas de valeur par défaut : un club dont les données de
contrat sont absentes ou clairsemées (`masse_salariale_actuelle` alors
nulle ou faible) garde un plafond raisonnable au lieu de se retrouver
bloqué à ~0. `marge_masse_salariale_initiale` (0.10) est la seule marge
de manœuvre au-delà des salaires déjà engagés. `masse_salariale_max`
n'est ensuite jamais recalculé (fixé à l'import, comme avant).

### Flux mensuel (`core/world/finances.py::appliquer_flux_mensuel`)

**Ajouté 2026-09-12, demande explicite de l'utilisateur** ("il faudrait
implémenter une notion de budget par équipe : dépenses = salaires chaque
mois + transferts, revenus = transferts + revenu mensuel billetterie/
merchandising + revenu annuel primes de classement"). Appelé chaque
1er du mois depuis `avancer_un_jour`, pour chaque club actif :

```python
depense = masse_salariale_actuelle(effectif) * semaines_par_an / 12                       # salaires
revenu = (masse_salariale_actuelle(effectif) * semaines_par_an / 12) / part_revenus_salaires  # billetterie/merchandising
club.solde += revenu - depense
club.budget_transfert += revenu - depense
```

**`revenu_mensuel` est ancré sur la masse salariale RÉELLEMENT payée
(`masse_salariale_actuelle`), pas sur la réputation ni sur le plafond**
— deux corrections successives le même jour :

1. Une première version dérivait le revenu de
   `calculer_revenus(reputation, pays)/12` : une fois le plafond salarial
   corrigé pour suivre les vrais salaires (section précédente), un revenu
   resté sur l'échelle de la réputation devenait comiquement trop petit
   pour les mêmes grands clubs (mesuré : Real Madrid avec une masse
   salariale réelle **sous** son propre plafond, mais un déficit mensuel
   chronique d'environ -11M€, atteignant -318M€ sur 4 saisons simulées).
2. La version suivante ancrait le revenu sur `masse_salariale_max` (le
   plafond, donc les vrais salaires, mais un **plafond fixe**) : à
   l'inverse, ça payait plein pot indépendamment de l'effectif réel — un
   club à l'effectif stabilisé n'ayant plus besoin d'acheter accumulait
   l'excédent sans jamais le dépenser (mercato plafonne le *nombre* de
   négociations par fenêtre, pas la dépense totale). Mesuré : plus d'un
   milliard d'euros de `budget_transfert` inutilisé pour Real Madrid après
   4 saisons. **Corrigé** en ancrant sur `masse_salariale_actuelle`
   (l'effectif réel) plutôt que sur le plafond : un effectif plus petit
   gagne aussi moins, au lieu d'un plafond qui paie sans rapport avec le
   vrai effectif.

Dans les deux cas la formule inverse `part_revenus_salaires` (0.62, déjà
la fraction du revenu que la masse salariale est censée représenter)
pour garantir, par construction, qu'elle n'en dépasse jamais cette
fraction — exactement l'intention d'origine, mais calée sur les vrais
salaires réellement payés plutôt que sur la réputation ou un plafond fixe.

**Conséquence : les salaires seuls ne peuvent plus mettre un club en
dette.** `revenu` et `depense` dérivent tous deux de la même
`masse_salariale_actuelle` avec une marge positive fixe (l'inverse de
`part_revenus_salaires`) — le flux mensuel est donc toujours positif ou
nul. Un déficit réel ne peut plus venir que d'un dépassement du budget
transfert à l'achat, déjà bloqué en amont par `_peut_se_permettre`
(`core/world/mercato.py`).

### Prime de classement (`core/world/saison.py`, à la bascule du 1er juillet)

**Ajoutée 2026-09-12, même demande.** `core/ai/budgets.py::prime_classement`
(extrait de `calculer_revenus`, même formule `bonus_classement_premier *
decroissance_par_place ** (place - 1)`) est versée une fois par an à
chaque club actif, contre sa place réelle dans le classement final que
`_relancer_saison_au_1er_juillet` vient de calculer et d'archiver — pas
contre une estimation. C'est le "recalcul annuel" documenté plus bas
(§ historique) comme non implémenté, désormais fait, mais sous forme
d'une prime versée directement plutôt que d'un recalcul de
`masse_salariale_max`/`budget_transfert` depuis zéro (`masse_salariale_max`
n'a de toute façon aucune raison de changer : voir plus haut).

### Historique : pourquoi `budget_transfert` et `solde` bougent ensemble

**Repéré en production (2026-09-11)** après avoir rendu le mercato
réellement actif cette session : sur 4 saisons simulées, 42 des 96 clubs
actifs sous 16 joueurs, certains grands clubs sous 10.
`calculer_budget_transfert`/`calculer_masse_salariale_max` n'étaient
calculées qu'à l'import, jamais recalculées — `budget_transfert` n'était
de ce fait débité par les achats que dans un seul sens : `solde`
encaissait bien le produit des ventes mais ne le reversait jamais dans le
budget dépensable. **Corrigé le jour même** (demande explicite) :
`core/world/mercato.py::_executer_transfert` réinjecte le montant d'une
vente dans le `budget_transfert` du vendeur, immédiatement, en plus de
`solde`. **Complété 2026-09-12** en corrigeant l'asymétrie côté achat
(`solde` de l'acheteur ne baissait pas, seul `budget_transfert` le
faisait) — sans ça, `solde` n'aurait jamais pu servir de référence
fiable pour le flux mensuel ci-dessus, qui doit pouvoir créditer/débiter
les deux indifféremment.

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
  **Bug trouvé en production, deuxième fois le même jour** : pouvoir
  payer ne veut pas dire y engager tout son budget — un club (AS Cannes)
  a dépensé 96% de son `budget_transfert` total sur un seul joueur de
  RC Lens. `part_budget_max_demarchage` (30%, config) relève le plancher
  de budget exigé d'un candidat plausible d'autant, plutôt que de se
  contenter de "peut payer en totalité". Vérifié sur une saison réelle :
  57 démarchages, aucun au-delà de 29,8% du budget engagé.
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
- **Urgence effectif (2026-09-11, ajoutée)** : sous `effectif_minimum_urgence`
  (16, config), un club plafonne à `negociations_actives_max_urgence`/
  `tentatives_prospection_max_urgence` (8/12) plutôt qu'aux valeurs
  normales (3/4) — garde-fou documenté (§7, "taille d'effectif 18-30,
  force l'achat sous 18") mais jamais implémenté avant qu'un vrai crash
  en production ne le rende nécessaire : un club tombé à 12 joueurs a
  fait planter `core/ai/selection.py` (effectif disponible sous
  `joueurs_sur_terrain`), et 13 des 96 clubs actifs étaient déjà sous 16
  joueurs après seulement 1,6 saison simulée. Un effectif exsangue a
  souvent plusieurs postes vides à la fois ; les plafonds normaux n'en
  auraient traité qu'une poignée par tour. Voir aussi §8, `_joueur_dummy` —
  un filet de sécurité complémentaire pour le cas où, malgré tout, un
  effectif tombe sous 11 joueurs disponibles un jour de match.
- **Hors périmètre, documenté dans `core/world/mercato.py`** : pas
  de prêt, clause libératoire, ni d'échange (`TransfertSec` — argent
  comptant seulement, voir `RegleTransfert` dans `docs/architecture.md`).

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

**Implémenté (2026-09-11), simplifié à deux issues** (demande
explicite de l'utilisateur) plutôt que trois : un club renouvelle, ou
ne fait rien et le contrat va à son terme — pas de "mise sur liste de
transfert" distincte. `core/world/contrats.py::renouveler_contrats`
appelle `decision_renouvellement` pour chaque joueur sous contrat d'un
club actif ; si `renouvelle`, le contrat est immédiatement remplacé
(nouveau salaire, nouvelle échéance) — sinon rien ne change, le joueur
continue de jouer sous son contrat actuel jusqu'à son terme naturel.

- **Vérifié mensuellement, pas chaque semaine comme documenté plus
  haut** : le chemin coûteux de `decision_renouvellement` (`utilite()`,
  un `meilleure_affectation`) se déclenche pour tout joueur à moins de
  `mois_avant_fin_declenchant` (12) de l'échéance — une bonne partie
  d'un effectif à un instant donné. Re-décider un joueur non renouvelé
  chaque jour pendant potentiellement un an referait cet appel coûteux
  pour rien (la décision ne dépend que du joueur/club/date, jamais de
  la dernière fois qu'elle a été posée) ; une fois par mois suffit et
  coûte 30x moins cher.
- **Tous les contrats générés (renouvellement ou transfert,
  `core/world/mercato.py::_executer_transfert`) se terminent
  désormais le 30 juin** (`config/monde.json ->
  dates_cles.liberation_contrats_expires`), convention explicite de
  l'utilisateur — pas nécessairement la vraie durée en années depuis la
  signature (un renouvellement signé en mars pour "1 an" dure en
  pratique ~15 mois jusqu'au 30 juin suivant), comme le fait le
  football réel. Les contrats importés (dates réelles du CSV) ne sont
  **pas** réécrits : `liberer_contrats_expires` compare `date_fin` à la
  date du jour plutôt que d'exiger une correspondance exacte, donc une
  échéance importée un peu décalée du 30 juin se libère quand même
  correctement au 1er juillet suivant.
- **`core/world/contrats.py::liberer_contrats_expires`**, chaque
  1er juillet : tout joueur d'un club actif dont le contrat est déjà
  échu (`date_fin <= date`) devient agent libre (`club_id = None`,
  `contrat = None`). Un joueur renouvelé entre-temps a déjà une
  échéance repoussée de plusieurs années — jamais concerné ici, aucun
  état à suivre séparément.
- **Bug trouvé en production, corrigé le jour même** : `decision_renouvellement`
  ne renouvelait qu'à condition que `utilite() > 0` — or `utilite()`
  passe par `meilleure_affectation` (gloutonne, même défaut que
  `core/world/mercato.py::_meilleur_candidat` déjà corrigé plus haut) :
  un effectif déjà saturé de très bons joueurs peut montrer un gain nul
  ou négatif à en garder un de plus, même s'il mérite clairement sa
  place. Repéré en simulant 4 saisons sur les vraies données : les plus
  grands clubs (Real Madrid, Barcelone, Man City) s'effondraient
  spécifiquement pour cette raison — leurs propres bons joueurs
  n'étaient jamais renouvelés, expiraient en agents libres pour rien,
  pendant que des clubs moyens s'en sortaient bien mieux. Un joueur qui
  dépasse toujours `niveau_cible(club)` est désormais renouvelé même si
  `utilite()` ressort à 0, en plus du critère existant.
- **`budget_transfert` réalimenté à la vente, pas seulement `solde`** :
  `calculer_budget_transfert`/`calculer_masse_salariale_max` (§4) ne
  sont calculés qu'une fois, à l'import, jamais recalculés ensuite —
  `budget_transfert` n'était donc débité par les achats que dans un seul
  sens. `core/world/mercato.py::_executer_transfert` réinjecte
  désormais le montant d'une vente directement dans le
  `budget_transfert` du vendeur (pas seulement `solde`, qui
  l'encaissait déjà sans jamais le reverser) — demande explicite de
  l'utilisateur, plutôt que d'attendre un recalcul annuel complet.
- **Signature d'un agent libre** : `core/world/mercato.py`'s boucle
  d'achat cible aussi les agents libres (`_pool_par_poste` ne les
  exclut plus). Pas de frais de transfert, pas de vendeur à convaincre
  — la signature passe par le même circuit offres/résolution qu'un
  transfert normal (plusieurs clubs intéressés le même tour sont
  départagés par `score_offre`, comme d'habitude) mais est acceptée
  d'office plutôt que soumise à `repondre_offre`.
- **Minutes non suivies** (voir aussi `docs/ui.md`) :
  `minutes_saison`/`minutes_attendues` valent 0/0 dans l'appel — la
  formule de `satisfaction()` traite déjà ce cas comme neutre
  (`s_jeu = 1.0` si `minutes_attendues` est nul), pas une valeur
  inventée.

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

**Joueurs "Dummy" de secours (2026-09-11, ajouté, demande explicite de
l'utilisateur après un crash réel en production)** : un effectif
appauvri en cascade (renouvellements non accordés, agents libres,
démarchages) peut tomber sous `joueurs_sur_terrain` (11) de joueurs
disponibles — `core/ai/selection.py::_selectionner_onze` n'a alors
littéralement personne à aligner pour un ou plusieurs postes, et
plantait (`IndexError`) avant ce correctif. `_joueur_dummy` complète
désormais le onze avec des joueurs de secours **transitoires** — jamais
écrits dans `Monde.joueurs`, id négatif, nom "Dummy" pour rester
identifiables — au niveau moyen de l'effectif de référence moins
`reduction_niveau_dummy` (20%, config). Complémentaire, pas un
remplacement, du vrai correctif de fond : voir "Boucle de mercato" plus
haut, `effectif_minimum_urgence`, pour ce qui évite qu'un effectif en
descende là en premier lieu.

## 9. Validation

Suite `economie` de `docs/benchmarks.md`, 25 saisons sans interface. Cibles dans
`config/benchmarks.json`.

Si le talent se concentre ou si les salaires explosent, le problème est presque
toujours dans les garde-fous, pas dans les heuristiques.
