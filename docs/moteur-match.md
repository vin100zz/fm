# Moteur de match

> Toutes les valeurs numériques de ce document sont dans `config/moteur_match.json`, `config/formations.json` et `config/implications.json`.
> Les tableaux ci-dessous documentent les valeurs initiales ; la source de
> vérité est le JSON. Aucune constante ne doit apparaître dans le code.

## État de l'implémentation (2026-09-10)

Le moteur par possessions est implémenté dans `src/core/engine/` (`possession.py`,
`notes_zones.py`, `composites.py`, `couloirs.py`, `occasion.py`,
`coups_arretes.py`, `cartons.py`, `chronologie.py`, `selection_joueur.py`,
`match.py`) et fonctionne de bout en bout (~6 ms/match, sous la cible de 20 ms).
Points à connaître avant d'y toucher :

**Formules non spécifiées ici, tranchées pendant l'implémentation** — ce
document ne donne pas `ajuster()` (résolution tir/tête contre gardien) ni la
pondération exacte de la vision dans le changement d'aile. `ajuster()` déplace
le log-odds du xG de base par l'écart de composite attaquant/défenseur
(`sensibilite_tireur_gardien`), de sorte que composites égaux reproduisent
le xG de base — voir le docstring dans `occasion.py`. Le changement d'aile
centre le taux configuré sur une vision moyenne de 50 (voir `couloirs.py`).

**Bug trouvé et corrigé en calibrant** : un contre qui échoue près du but
redéclenchait un nouveau contre pour l'autre équipe, en boucle — un match
produisait 150+ tirs. Corrigé : un contre qui échoue retombe en zone
`DEFENSE`, il ne s'enchaîne jamais directement dans un autre contre (voir le
commentaire dans `match.py::_possession_suivante`).

**Volontairement hors périmètre pour cette passe**, pas oublié : forme/fatigue/
moral sont lus une fois au coup d'envoi (pas de dynamique en cours de match,
ni recalcul aux paliers de fatigue — la vraie dynamique de fatigue est
l'étape 6) ; pas de remplacement en cours de match (besoin de
`AIController.decider_remplacement`, étape 7) ; pas de blessure en match
(étape 6) ; `hauteur_bloc` existe sur `Equipe` mais n'est pas encore consommé
par le moteur (zone de récupération, vulnérabilité au contre — à ajouter
quand ces effets seront calibrés) ; le gardien ne peut jamais être expulsé
(pas de remplacement par un joueur de champ dans ce modèle).

**Calibrage (mis à jour le 2026-09-11)** : les suites `stats_match_possession`
et `match_possession` (`src/benchmarks/suites/`) font tourner le vrai moteur
par possessions — réimport frais de `data/` à chaque exécution plutôt qu'un
instantané figé, puisque rien ne peut encore faire dériver un effectif d'une
exécution à l'autre (pas de mercato). `stats_match_possession` est au vert
sur 6 cibles sur 7 :

| Cible | Résultat | Statut |
|---|---|---|
| Tirs par équipe | 12.9 | OK |
| xG par équipe | 1.41 | OK |
| Possession | 50 % | OK |
| Jaunes par équipe | 1.99 | OK |
| Rouges par équipe | 0.059 | OK |
| Part de buts sur CPA | 0.277 | OK |
| Répartition par couloir | 25/49/25 (G/A/D) | ECHEC |

Coefficients retenus : `transitions.k_prog=0.116`,
`occasion.xg_base_frappe=0.092`, `occasion.xg_base_centre=0.076`,
`coups_arretes.xg_base_corner=0.21`,
`cartons.probabilite_jaune_par_turnover_defensif=0.0075`,
`cartons.probabilite_rouge_direct_par_turnover_defensif=0.00025`.

**Répartition par couloir : limite structurelle, pas un coefficient à
régler.** Ni `beta_softmax` (0.01 à 0.05 testés, aucun effet) ni
`probabilite_changement_aile` (testé jusqu'à 0.02) ne rapprochent l'axe de
33 % — le faire baisser suffisamment romprait la cible de changement d'aile
(15-20 % des progressions). La cause réelle : la plupart des postes d'un
onze pèsent majoritairement sur l'axe dans `implications.json → lateral`
(GB, DC, MDC, MC, MOC à 60 %), donc l'axe domine mécaniquement le choix de
couloir quel que soit l'écart de force. Non résolu — nécessiterait de revoir
les poids latéraux eux-mêmes, une décision de contenu, pas un balayage.

**`match_possession` : les favoris ne gagnent pas assez souvent**, même
après calibrage de `stats_match_possession` (ex. PSG bat Toulouse 57 % du
temps contre 75 % visé). Balayé `k_occ` de 0.11 à 0.19 sans tendance claire.
Cause probable : même limite que documentée dans `docs/benchmarks.md` pour
le moteur analytique — la synthèse d'attributs v0 (`docs/modele-donnees.md`)
sature en haut d'échelle et comprime l'écart de force réel entre équipes
« très fortes » et « fortes » (Man City/Burnley n'a jamais convergé non plus,
pour la même raison). Pas un problème de coefficient de moteur : à revisiter
quand de vraies données d'attributs remplaceront la synthèse.

## Deux moteurs

**Moteur analytique** (à écrire en premier, à conserver ensuite)

Calcule une force d'attaque et de défense par équipe, en déduit un nombre de buts
attendus, tire le score dans une loi de Poisson. Sert d'oracle de référence et de
mode rapide pour simuler en masse. Une centaine de lignes.

**Moteur par possessions** (le moteur de production)

Simule le match possession par possession. C'est celui qui produit les
événements, les statistiques par joueur et le compte rendu.

Les deux doivent produire des distributions de résultats compatibles. Un écart
signale un bug dans le second.

## Structure de la simulation

Un match est une suite de possessions, pas une suite de minutes. Environ 200 à
240 possessions au total, 100 à 120 par équipe.

```python
def simuler_match(dom, ext, rng) -> ResultatMatch:
    notes = {dom: notes_zones(dom), ext: notes_zones(ext)}
    t, score, evenements = 0, [0, 0], []
    poss = engagement(rng)

    while t < 90 * 60:
        t += duree_possession(rng)          # moyenne 22 s, loi Gamma
        res = jouer_possession(poss, notes, t, rng)
        appliquer(res, score, evenements)
        poss = possession_suivante(res, rng)

    return assembler_resultat(score, evenements)
```

Recalculer `notes_zones` **uniquement** aux changements : remplacement, carton
rouge, palier de fatigue franchi. Pas à chaque possession.

## Géométrie

**4 zones verticales** : `DEFENSE`, `MILIEU_BAS`, `MILIEU_HAUT`, `VERITE`
**3 couloirs** : `GAUCHE`, `AXE`, `DROITE`

La zone est l'axe de la machine à états, elle pilote les phases. Le couloir est
une propriété de la possession, qui peut changer en cours de route.

## Machine à états d'une possession

```python
def jouer_possession(p, notes, t, rng):
    while True:
        A = notes[p.equipe].att[p.zone][p.couloir]
        D = notes[p.adverse].dfn[p.zone][p.couloir]

        if p.zone < VERITE:
            if not reussite(k_prog * (A - D) + bonus_dom, rng):
                return Turnover(zone=p.zone, couloir=p.couloir)
            p.zone += 1
            p = peut_changer_aile(p, notes, rng)
        else:
            if not reussite(k_occ * (A - D), rng):
                return Turnover(zone=p.zone, couloir=p.couloir)
            return resoudre_occasion(p, notes, rng)
```

Toutes les probabilités de transition ont la forme :

```python
def reussite(x, rng, biais=0.0):
    return rng.random() < 1 / (1 + exp(-(x + biais)))
```

## Agrégats de zone — la formule qui compte

C'est la partie la plus délicate du moteur. Elle doit séparer **qualité** et
**densité**, sinon les formations défensives ne fonctionnent pas.

```python
def note_zone(equipe, zone, couloir, phase):
    poids = [impl(j, zone, couloir, phase) for j in equipe.onze]
    densite = sum(poids)
    if densite == 0:
        return NOTE_PLANCHER

    qualite = sum(
        p * composite(j, phase) * j.forme * j.fatigue * j.moral_mult * j.malus_poste
        for p, j in zip(poids, equipe.onze)
    ) / densite

    return qualite * facteur_densite(densite)
```

**Pourquoi la division** : sans elle, un 5-4-1 gagne mécaniquement toutes les
zones défensives parce qu'il y a plus de joueurs dedans, et les agrégats sortent
de l'échelle 1-100. C'est le bug le plus courant de ce type de moteur.

**Pourquoi le facteur de densité** : avec la seule moyenne, aligner un cinquième
défenseur ne change rien — pire, s'il est moins bon, la moyenne baisse.

```python
D_REF = 3.5

def facteur_densite(d):
    return (d / D_REF) ** 0.5
```

L'exposant 0.5 fait saturer : le troisième joueur d'une zone apporte beaucoup, le
sixième presque rien. C'est le bouton d'équilibrage des formations.

Avec cette formule, `A - D` reste lisible : un écart de 10 signifie dix points de
niveau.

## Formations

Aucune formation n'est traitée par du code spécifique. Une formation est
uniquement **une liste de postes**, qui remplit la matrice d'implication.

La conservation fait le reste : chaque joueur dispose d'un budget d'implication
à peu près constant, donc empiler à l'arrière vide l'avant automatiquement.

Densités totales attendues, en défense et en attaque :

| Zone | 4-3-3 déf | 5-4-1 déf | 4-3-3 att | 5-4-1 att |
|---|---|---|---|---|
| Défense | 3.8 | 5.2 | 0.8 | 0.5 |
| Milieu bas | 3.2 | 4.0 | 2.4 | 1.6 |
| Milieu haut | 1.8 | 1.2 | 3.4 | 2.2 |
| Vérité | 0.6 | 0.2 | 2.6 | 1.0 |

**Interdit** : toute table de contres du type « 5-4-1 bat 4-3-3 avec +8 % ».
L'avantage doit naître du calcul zone par zone, sinon le jeu se réduit à
connaître la table.

Formations à supporter en v1 : 4-4-2, 4-3-3, 4-2-3-1, 3-5-2, 5-3-2, 5-4-1.

## Hauteur de bloc

Axe **indépendant** de la formation : un 4-3-3 peut jouer bas, un 5-4-1 peut
presser haut.

```python
h: float  # -1.0 (bloc bas) à +1.0 (pressing haut)
```

Deux effets, et seulement deux :

1. **Zone de récupération** après turnover adverse. Bloc haut, on récupère en
   zone 3 plutôt qu'en zone 1.
2. **Vulnérabilité au contre**. Bloc haut, l'adversaire qui franchit la première
   ligne saute une zone et arrive directement en situation dangereuse.

## Choix du couloir

Softmax sur l'écart de force, jamais uniforme :

```python
BETA = 0.06

def choisir_couloir(notes, zone, equipe, adverse, rng):
    ecarts = [notes[equipe].att[zone][c] - notes[adverse].dfn[zone][c]
              for c in COULOIRS]
    poids = [exp(BETA * e) for e in ecarts]
    return tirage_pondere(COULOIRS, poids, rng)
```

Une équipe attaque plus souvent de son côté fort et cible le latéral faible d'en
face. Intelligence tactique émergente, sans code d'IA. `BETA` bas au départ :
trop élevé, 90 % des attaques passent du même côté.

**Changement d'aile** : à chaque progression, probabilité de basculer vers un
couloir voisin, pondérée par la vision du milieu de la zone courante. Empêche les
attaques d'être des couloirs figés. Viser 15 à 20 % des progressions.

## Résolution de l'occasion

Le couloir détermine le type d'occasion.

```python
def resoudre_occasion(p, notes, rng):
    if p.couloir in (GAUCHE, DROITE):
        return resoudre_centre(p, notes, rng)
    return resoudre_frappe(p, notes, rng)
```

**Centre** : tirer un centreur (pondéré par implication dans le couloir), puis un
réceptionneur (pondéré par implication en zone `VERITE`). xG de base faible.

```python
xg_centre = 0.06 * f(comp_tete_receptionneur, comp_sortie_gardien)
```

**Frappe axiale** : tirer un tireur pondéré par implication. xG plus élevé,
majoré si la possession vient d'un contre.

```python
xg_frappe = 0.11 * (1.6 if p.est_contre else 1.0)
```

Puis résolution contre le gardien, dans les deux cas :

```python
p_but = ajuster(xg, comp_tir_ou_tete, comp_arret_gardien)
```

**Ne pas ajouter de dimension latérale au tir lui-même** : la position est déjà
encodée dans le xG, une dimension supplémentaire ne ferait que diluer la finition.

## Turnovers et contres

La **position de la perte de balle** détermine tout. C'est le mécanisme qui rend
les matches vivants et récompense les profils rapides.

- Perte en zone 1 ou 2 → possession adverse normale, en zone symétrique
- Perte en zone 3 ou 4 → **contre** : l'adversaire démarre en zone avancée, dans
  le même couloir, avec un malus défensif temporaire pour l'équipe qui vient de
  perdre le ballon, et `est_contre = True` sur la possession

Le malus s'applique surtout au couloir concerné : le latéral de ce côté est hors
position. C'est ce qui rend un latéral offensif réellement risqué.

## Coups de pied arrêtés

Environ 25 à 30 % des buts réels. Branche séparée, peu de code, mais elle donne
une raison d'exister aux grands défenseurs.

- Corner ou coup franc généré à partir d'un turnover en zone avancée
- Réceptionneur tiré parmi **tout le onze**, pondéré par `jeu_tete`
- Gardien résiste avec `comp_sortie`
- xG autour de 0.04 par corner

## Avantage du terrain

Un seul point d'application : `bonus_dom` dans la probabilité de progression.
Ne pas l'appliquer sur les buts directement. Calibrer pour obtenir environ
+0.3 but par match.

## Fin de match

Temps additionnel : 2 à 5 minutes, tiré aléatoirement, majoré par le nombre
d'arrêts de jeu (buts, remplacements, blessures).

Une équipe menée en fin de match augmente sa hauteur de bloc. Effet simple,
proportionnel à l'écart au score et au temps restant.

## Cibles de calibrage

À atteindre **dans cet ordre**. Ne pas toucher aux ratios victoire/nul/défaite
avant que ces chiffres-là soient justes.

Par match et par équipe :

| Métrique | Cible |
|---|---|
| Possessions | 100 – 120 |
| Tirs | 12 – 14 |
| xG cumulé | 1.3 – 1.5 |
| Buts | 1.35 (2.7 par match) |
| Possession | 45 – 55 % |
| Avantage domicile | +0.3 but |
| Buts sur coup de pied arrêté | 25 – 30 % |
| Répartition par couloir | ~33 % chacun |
| Dangerosité par attaque | axe > ailes |

Une fois ces chiffres tenus, l'objectif « le PSG bat Toulouse 70 / 20 / 10 » se
règle avec `k_prog` et `k_occ`, les coefficients qui disent à quel point l'écart
de talent est décisif. C'est le seul bouton de « part d'aléatoire ».

Piège classique : trop peu d'aléatoire. Un moteur naïf fait gagner le favori 95 %
du temps, alors que le football réel plafonne vers 65-70 %.

## Calibrage

Le harnais, les suites et les critères d'échec sont dans `docs/benchmarks.md`.
Les cibles chiffrées sont dans `config/benchmarks.json`.

Rappel de l'ordre : valider `stats_match` (le match ressemble à un match), puis
`formations` (aucune formation ne domine), puis seulement `match` (les bons
favoris gagnent dans les bonnes proportions). Les coefficients de chaque étape
dépendent des précédentes.
