# Progression, déclin, démographie

> Toutes les valeurs numériques de ce document sont dans
> `config/demographie.json`. Les tableaux ci-dessous documentent les valeurs
> initiales ; la source de vérité est le JSON.

## État de l'implémentation (2026-09-11)

"Progression et déclin" ci-dessous est implémenté dans
`src/core/world/progression.py` (`progresser`, `facteur_par_age`) — voir
`docs/etats-joueur.md` pour l'état d'ensemble de l'étape 6. `appliquer_delta`
(non nommée dans ce document) ajoute le delta uniformément sur les 13
attributs en croissance (ce qui augmente `note_globale` d'exactement ce
delta, ses poids sommant à 1.0), et le repondère par
`poids_declin_par_attribut` en décroissance. Une subtilité du formule
documentée telle quelle : si `marge` (potentiel − niveau actuel) vaut 0,
le terme d'âge s'annule et seul le bruit gaussien s'applique, même pour un
joueur très âgé — un joueur exactement à son potentiel ne décline donc pas
automatiquement par le seul effet de l'âge tant que le bruit ne le pousse
pas en dessous. Pas retouché, c'est le comportement exact de la formule
documentée.

La génération de regens et le pilotage démographique ("Démographie" et
sections suivantes) sont implémentés dans `src/core/world/demographie/`
(étape 8) :

- `generation.py` : le tirage complet d'un joueur (§"Tirage d'un joueur")
  et `promouvoir_centre_formation` (§"Centres de formation").
- `identite.py` : pools de noms et tirage d'identité (§6, voir la note
  dédiée ci-dessous).
- `cohorte.py` : la boucle de rétroaction (`corriger`, `corriger_poids`)
  et le comptage de population par poste/nation/palier de niveau.
- `sorties.py` : `probabilite_retraite` et `sort_du_perimetre`.

Plus deux ajouts à des fichiers existants pour le marché extérieur :
`core/world/progression.py::progresser_dormant` et
`core/ai/mercato.py::repondre_offre_dormant`.

**Retraites et promotions du centre de formation câblées sur un
calendrier (2026-09-12, ajouté, demande explicite de l'utilisateur)** —
`core/world/demographie/cycle_annuel.py::appliquer_cycle_annuel_effectif`,
appelé depuis `core/world/saison.py::avancer_un_jour`, une fois par an à
`config/monde.json -> dates_cles.promotion_centre_formation` (15 juin,
la date que ce document nommait déjà sans qu'elle serve nulle part).
`probabilite_retraite` (pure depuis l'étape 8) retire désormais pour de
vrai un joueur du monde (`del Monde.joueurs[...]`) quand le tirage
tombe dessous, pour tout joueur d'un club actif ; `promouvoir_centre_formation`
(pure depuis l'étape 8) alimente chaque club actif en jeunes joueurs. Les
deux événements sont journalisés dans `Monde.historique.mouvements_effectif`
(nouveau, `core/domain/historique.py`) pour l'onglet "Transferts" d'une
fiche club (`docs/ui.md`), aux côtés des départs libres en fin de contrat
(`liberer_contrats_expires`, désormais lui aussi journalisé de la même
façon). **Reste volontairement hors périmètre** : la boucle de
rétroaction démographique complète (`cohorte.py`, comparer la population
observée à la cible par tranche) — seuls les événements *par club actif*
nécessaires à l'onglet Transferts sont câblés, pas le rééquilibrage de
l'ensemble de la population des ~32 000 joueurs, un chantier séparé et
plus large. Le flux entre monde actif et dormant
(`docs/modele-donnees.md`, `part_transferts_depuis_dormants`) n'est pas
mesuré non plus, faute de boucle de mercato pour le produire (voir
`docs/ia-gestion.md`).

**Aucune liste de prénoms/noms n'a été fournie** (seuls `data/clubs.csv`
et `data/players.csv` existent — voir `docs/modele-donnees.md`) : les
pools de `identite.py` sont construits depuis la population déjà
importée elle-même, groupée par `Joueur.nationalite`. C'est gratuit et
réaliste (un pool par nation avec sa vraie distribution de noms), au prix
d'un couplage : la nation d'un régen doit être exprimée dans le même
vocabulaire que `Joueur.nationalite` (le libellé français brut de la
colonne "Nation" du CSV, ex. "France", "Angleterre" — pas le code ISO
court `pays` utilisé par ailleurs pour `Club.pays`, ex. "FRA", "ENG").
`config/monde.json -> competitions_simulees[].nationalite_source` fait le
pont entre les deux vocabulaires, en config plutôt que codé en dur.

**Formules non données par le document, tranchées pendant
l'implémentation** :

- La "force" d'une nation (§1, alpha/beta du tirage de potentiel) réutilise
  `ia_gestion.budgets.revenus.multiplicateur_pays` (déjà calibré) plutôt
  qu'un nouveau paramètre indépendant :
  `alpha_nation = alpha_moyen * multiplicateur^exposant_force_nation`,
  `beta_nation = beta_moyen / multiplicateur^exposant_force_nation` —
  toujours positif, aucun clamp nécessaire. Voir `config/demographie.json
  -> nations`.
- Le "poids de production" par nation (§1) n'est pas une table
  indépendante : il est réparti au prorata de
  `monde.competitions_simulees[].nb_clubs` (déjà en config) à partir d'un
  seul scalaire, `nations.poids_total_ligues_simulees` — le résidu va au
  vivier extérieur.
- `corriger(cible, observe)` (§"Boucle de rétroaction") compare des
  **comptes bruts**, pas des proportions — c'est ce que
  `max(observe, 1)` suppose (un bucket vide vaut 0 en proportion, pas 1).
  `cohorte.py::corriger_poids` convertit la cible (proportion) en compte
  attendu avant de comparer, puis renormalise.

## Progression et déclin

Même sans entraînement, le monde doit bouger. Sinon tout se fige en trois
saisons.

Évaluation **mensuelle**, pas quotidienne.

```python
def progresser(joueur, minutes_mois, rng):
    marge = joueur.potentiel - note_globale(joueur)
    facteur_age = courbe_progression(joueur.age)
    facteur_jeu = 0.35 + 0.65 * min(minutes_mois / 400, 1.0)

    delta = facteur_age * facteur_jeu * (marge / 100) * 2.2 + rng.gauss(0, 0.25)
    appliquer_delta(joueur, delta)
```

### Courbe de progression par âge

| Âge | Facteur |
|---|---|
| 16 – 19 | +1.00 |
| 20 – 22 | +0.75 |
| 23 – 25 | +0.40 |
| 26 – 28 | +0.10 |
| 29 – 30 | −0.15 |
| 31 – 32 | −0.45 |
| 33 – 34 | −0.85 |
| 35+ | −1.30 |

### Règles

- La progression est **plafonnée par le potentiel**, jamais dépassé
- Le déclin ne l'est pas : un joueur de 36 ans descend sous son niveau passé
- Le déclin frappe d'abord `vitesse` et `endurance`, puis les attributs
  techniques, et épargne largement `placement`, `vision` et `sang_froid`
- Le temps de jeu compte : un jeune qui ne joue pas progresse trois fois moins
  vite. C'est ce qui rend les prêts intéressants quand ils seront ajoutés
- Échantillonner et stocker la note globale une fois par saison, pour la courbe
  de carrière affichée sur la fiche joueur

## Estimation du potentiel

Le `potentiel` stocké est la valeur vraie. **Ni l'IA ni l'interface ne doivent y
accéder directement.**

```python
def estimation_potentiel(joueur, club_observateur=None) -> Fourchette:
    bruit = 22 * (1 - min(joueur.age - 15, 8) / 8)
    if club_observateur:
        bruit *= (1.3 - 0.5 * club_observateur.reputation / 100)
    return Fourchette(joueur.potentiel - bruit, joueur.potentiel + bruit)
```

L'incertitude se resserre avec l'âge et avec la qualité de l'observateur. Sans
elle, il n'y a aucun risque à recruter un jeune, donc aucun intérêt.

## Démographie

Ce n'est pas de la génération de joueurs à la demande : c'est le pilotage d'une
population en régime permanent.

```
Cible démographique  →  Cohorte annuelle  →  Population active  →  Sorties
                              ↑                      |
                              └──── écart mesuré ────┘
```

### Conservation

En régime stable, entrées = sorties.

| Grandeur | Valeur |
|---|---|
| Population active | ~2 600 |
| Carrière moyenne | ~15 ans |
| Cohorte annuelle | **~175 joueurs** |

Dimensionner la cohorte sur les **départs réels de l'année**, pas sur un nombre
fixe.

### Le piège des espérances de carrière

La distribution de la population active n'est pas la distribution de génération :

```
population(niveau) = génération(niveau) × carrière(niveau)
```

La carrière s'allonge avec le niveau : un joueur à 85 joue jusqu'à 36 ans, un
joueur à 55 disparaît vers 26. Donc il faut inverser :

```
génération(niveau) ∝ cible(niveau) / carrière(niveau)
```

**Il faut générer proportionnellement plus de joueurs faibles que la cible ne le
suggère.** Un échantillonnage naïf sur la distribution cible fait gonfler l'élite
saison après saison.

Cas d'école : le gardien. Il en faut ~10 %, mais sa carrière est bien plus
longue. Générer 10 % de gardiens en donne 14 % au bout de vingt saisons, tous
vieux.

### Boucle de rétroaction — le point clé

Même juste, le calcul en boucle ouverte dérive : blessures, comportements de
l'IA, règles de retraite, tout ce qui n'est pas modélisé s'accumule.

Chaque été, comparer la population observée à la cible, bucket par bucket :

```python
KAPPA = 0.30

def corriger(cible, observe):
    return (cible / max(observe, 1)) ** KAPPA
```

L'exposant amortit. Sans lui le système oscille : surproduction de gardiens une
année, pénurie la suivante.

**Appliquer la correction séparément sur chaque axe** (niveau, poste, nation),
jamais sur leur produit — sinon on obtient des milliers de buckets tous vides.

C'est ce contrôleur, et non la qualité du tirage initial, qui garantit la
stabilité sur trente saisons.

## Tirage d'un joueur

Dans cet ordre.

### 1. Nation

Chaque pays porte un poids de production et une force de football propre.
Les 5 pays simulés produisent la majorité des joueurs ; le reste vient d'un
**vivier externe abstrait** (voir plus bas).

### 2. Potentiel

Loi à forte asymétrie droite :

```python
potentiel = 35 + 65 * rng.betavariate(alpha, beta)
```

Avec `alpha = 2.0`, `beta = 5.0` pour une nation moyenne. Une nation forte
monte `alpha`, une nation faible monte `beta`. Beaucoup de joueurs vers 50-60,
très peu au-dessus de 85.

### 3. Poste

Tiré sur la cible corrigée, avec affinités secondaires pour permettre les
reconversions.

Cible de population active :

| Poste | Part |
|---|---|
| GB | 10 % |
| DC | 18 % |
| DL / DR | 14 % |
| MDC / MC | 24 % |
| MOC | 11 % |
| AIL | 12 % |
| BU | 11 % |

### 4. Niveau actuel

```python
niveau = potentiel * g(age) * rng.gauss(1.0, 0.06)
```

Avec `g(16) ≈ 0.40`, `g(18) ≈ 0.50`. À 16 ans un joueur montre à peine la moitié
de ce qu'il sera.

### 5. Attributs

Répartis autour du niveau selon le profil de poste défini dans
`docs/attributs.md`, avec bruit gaussien d'écart-type 6.

### 6. Identité

Prénom et nom tirés des listes pondérées de la nation. Vérifier l'unicité du
couple (prénom, nom) dans la population active ; retirer en cas de collision.

## Centres de formation

Génération rattachée aux clubs, à date fixe (mi-juin), ce qui crée un rendez-vous
annuel visible dans l'interface.

```python
def promotion_centre(club, rng):
    n = rng.randint(2, 5)
    moyenne = 30 + 0.30 * club.reputation + 0.25 * club.note_centre_formation
    ...
```

**Mettre beaucoup de variance et des queues épaisses.** Si un petit club ne peut
jamais sortir un joyau, la journée du centre de formation est prévisible et sans
intérêt. Écart-type d'au moins 14 sur le potentiel, avec une probabilité non
nulle de dépasser 85 même pour un club de réputation 40.

Les jeunes issus du centre signent un contrat de 3 ans à salaire faible.

## Marché extérieur : les clubs dormants

Les ~25 900 clubs non simulés **sont** le marché extérieur. Il n'y a pas de
vivier artificiel à générer : les données fournies contiennent déjà les
divisions inférieures et les autres pays.

### Comportement

- Leurs joueurs progressent selon un modèle allégé : courbe d'âge seule, sans
  temps de jeu ni forme. Coût négligeable pour 30 000 joueurs, et le marché ne se
  fige pas.
- Ils répondent aux offres des clubs actifs selon une heuristique simple
  (`ia.mercato.clubs_dormants`) : acceptation probable au prix de marché majoré.
- Ils démarchent occasionnellement les joueurs des clubs actifs en fin de contrat
  ou en surplus, ce qui donne une sortie aux joueurs devenus inutiles.
- Ils produisent leurs propres regens, mais en volume réduit et sans détail.

### Conséquence sur la démographie

La population à piloter n'est plus les seuls 2 400 joueurs des clubs actifs, mais
l'ensemble des 32 000. Deux régimes distincts :

| Population | Pilotage |
|---|---|
| Clubs actifs (~2 400) | boucle de rétroaction complète, sur les 3 axes |
| Clubs dormants (~29 600) | conservation simple : cohorte = sorties, sans correction fine |

La cible de ~175 regens par an concerne les **clubs actifs**. Les dormants
génèrent séparément, avec une cohorte proportionnelle à leur population et une
distribution de niveau centrée plus bas.

### Flux entre les deux mondes

- Un joueur acheté par un club actif quitte le monde dormant et entre dans le
  régime complet
- Un joueur vendu à un club dormant en sort
- Ce flux doit représenter 25 à 40 % des transferts entrants des clubs actifs
  (`benchmarks.economie.part_transferts_depuis_dormants`). S'il tombe à zéro,
  l'économie des 5 championnats s'est refermée et le benchmark échoue.

## Sorties

Deux mécanismes distincts. **Le second est le plus souvent oublié et le plus
important.**

### Retraite

```python
def p_retraite(joueur):
    if joueur.age < 31: return 0.0
    base = 0.04 * (joueur.age - 30) ** 1.9
    return base * (1.4 - 0.6 * note_globale(joueur) / 100)
```

Un joueur faible raccroche plus tôt qu'une star. Évaluée en fin de saison.

### Abandon

Un joueur de 22 ans à 45 de niveau avec 48 de potentiel, dans un système dont le
plancher est à 55, **redescend vers un club dormant**. Il ne disparaît pas : il
reste consultable, et pourra remonter s'il progresse.

```python
def sort_du_perimetre(joueur):
    return (joueur.age >= 21
            and estimation_potentiel(joueur).max < SEUIL_PERIMETRE
            and joueur.club_id is None)
```

Sans ce mécanisme, les effectifs des clubs actifs se remplissent de médiocrité.
C'est le pendant naturel de l'achat depuis les dormants.

## Validation

Suite `demographie` de `docs/benchmarks.md`, 30 saisons. Cibles dans
`config/benchmarks.json`.

Le nombre de joueurs au-dessus de 85 est **l'indicateur canari** : statistique de
queue, il dérive en premier et de loin. Le surveiller à chaque modification du
modèle de progression.
