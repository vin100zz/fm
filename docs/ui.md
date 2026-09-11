# Interface

## Boucle de mercato (2026-09-11, ajouté après l'étape 9)

Implémenté : `core/world/mercato.py::tour_mercato`, appelé depuis
`avancer_un_jour` chaque jour de fenêtre été/hiver — voir "Boucle de
mercato" dans `docs/ia-gestion.md` pour le détail (convergence des
négociations, garde-fous de budget, un vrai bug de convergence trouvé et
corrigé dans `repondre_offre`). Les transferts effectifs apparaissent
maintenant :

- dans le journal du jour (`TypeEvenementJour.TRANSFERT`) ;
- dans `Monde.historique.transferts` (nouveau champ `saison` sur
  `TransfertHistorique`, comme `Match.saison`) ;
- via `GET /api/clubs/{id}/transferts` (nouveau) et l'onglet
  "Transferts" du club côté `web/` — arrivées et départs, montant,
  club source/cible, avec liens vers la fiche joueur et les clubs
  impliqués.

Reste non consultable dans l'interface : la liste des négociations *en
cours* (`Monde.negociations`) — seuls les transferts *conclus*
apparaissent, conformément à la contrainte v1 observateur (l'utilisateur
ne pilote ni ne voit les tractations d'un club, seulement leurs résultats).

## Sauvegarde/chargement (2026-09-11, ajouté après l'étape 9)

Implémenté : `core/world/persistance.py` (`sauvegarder`, `charger`,
`lister_sauvegardes`) et `api/routes_partie.py`. Sérialisation générique
pilotée par les type hints plutôt qu'une fonction par type de domaine :
`dataclasses.fields` pour parcourir un objet, `typing.get_type_hints`
(mis en cache par classe — sinon 32 000 `Joueur` refont la même
résolution 32 000 fois) pour reconstruire, avec un cas particulier pour
les `Enum` (valeur) et `X | None`. Un nouveau champ de domaine n'a donc
rien à faire ici — même esprit que le reste du projet.

**Le flux aléatoire est sauvegardé, pas seulement la graine.**
`Random.getstate()` est lui-même sérialisable (son tuple interne
converti en liste) ; le restaurer via `setstate()` reprend exactement la
même séquence là où la sauvegarde l'a coupée, plutôt que rejouer depuis
le début de la graine (`Monde.graine` reste stocké séparément — c'est ce
que CLAUDE.md documente pour une partie rejouée *depuis le début*, pas
pour une reprise). Vérifié par round-trip exact sur le monde réel à 32
000 joueurs (`monde_charge == monde_original`, `tests/unit/world/
test_persistance.py` + `tests/integration/api/`) et par continuité du
flux aléatoire après reprise.

**Format** : JSON gzippé (CLAUDE.md), `compresslevel=1` — la compression
maximale (défaut de `gzip.compress`) prenait ~3.3 s à elle seule sur le
monde complet pour ~10 % de taille en moins ; au niveau 1 la sauvegarde
prend ~1.5 s (le chargement, dominé par la reconstruction récursive,
~2.5 s). Les fichiers vivent dans `saves/` à la racine (gitignored,
comme `data/` n'est pas versionné) ; le nom de slot est assaini
(alphanumérique/`-`/`_`) côté serveur avant de construire le chemin.

**Front** : barre sous la navigation (`#barre-partie`) — champ de nom,
liste déroulante des sauvegardes existantes, boutons Sauvegarder/Charger.
Charger redemande confirmation (`confirm()` natif) avant d'écraser l'état
courant.

## Fin de saison (2026-09-11, ajouté après l'étape 9 ; règle du 1er
juillet précisée le même jour, sur demande explicite)

Implémenté : `core/world/saison.py::_relancer_saison_au_1er_juillet`,
appelé à la fin de chaque `avancer_un_jour`. **Une saison par an, du
1er juillet N au 30 juin N+1** (règle explicite) : toutes les
compétitions basculent **ensemble**, le jour où `monde.date` franchit
le 1er juillet — pas indépendamment dès que le calendrier de chacune
est épuisé (Ligue 1 à 18 clubs/34 journées et La Liga à 20/38 finissent
quand même de jouer à des dates différentes, vers avril-mai avec
l'espacement configuré ; c'est juste que la bascule *administrative* —
archivage et relance — n'a plus lieu qu'à cette date commune). Au
1er juillet :

1. pour chaque compétition, le classement final des matchs **effectivement
   joués** est archivé dans `Monde.historique.palmares`
   (`SaisonTerminee`, nouveau type) — une saison non entièrement jouée à
   l'échéance se clôture quand même sur ce qui a été disputé, plutôt que
   de rester bloquée indéfiniment ;
2. le cumul de cartons jaunes de la saison est remis à zéro pour les
   joueurs des clubs de cette compétition
   (`core.world.etats.suspensions.reinitialiser_saison`, une fonction
   prête depuis l'étape 6 que rien n'appelait encore) ;
3. un nouveau calendrier est généré pour les **mêmes** `club_ids`, dont
   le premier match n'est programmé qu'au prochain
   `config/monde.json -> saison.debut_mois/jour` (mi-août) — pas le
   lendemain du 1er juillet — laissant le creux estival où vit la
   fenêtre de mercato d'été.

**Pas de promotion/relégation** : c'était le périmètre convenu.
`Competition.appliquer_fin_saison` (docs/architecture.md) n'est donc
toujours pas implémenté — seule la partie "reconduire la même
compétition" l'est. `Match` porte un champ `saison` (sans ça, le
classement d'une saison 2 se mélangerait avec celui de la saison 1) ;
`Competition.saison_actuelle` suit l'édition en cours (les 5
compétitions partagent maintenant toujours la même valeur, puisqu'elles
basculent ensemble) ; `Monde.saison` n'est qu'un affichage global qui
en reprend le maximum.

`avancer_jusqua_journee` (bouton "avancer à la prochaine journée") a dû
passer sa limite par défaut de 30 à 120 jours : le creux estival entre
le dernier match d'une saison (~avril/mai) et le coup d'envoi de la
suivante (mi-août) dure lui-même ~100 jours sans aucun match programmé.

`GET /api/competitions/{id}/classement` et `.../calendrier` (et
`GET /api/clubs/{id}/calendrier`) ne montrent que la saison en cours —
`GET /api/competitions/{id}/historique` (nouveau) expose le palmarès :
champion et classement final par saison passée, mais **pas** le
meilleur buteur/passeur (toujours aucune agrégation de stats de match
par joueur, voir plus bas).

Vérifié par `tests/unit/world/test_saison.py::TestFinDeSaison` sur un
monde synthétique à 4 clubs (une vraie saison des 5 championnats est
bien trop longue — 34 à 38 journées — pour être jouée dans un test).

## État de l'implémentation (2026-09-11)

Étape 9, la dernière de l'ordre de construction. Contrairement aux étapes
précédentes, celle-ci a dû construire au passage la pièce que chaque étape
depuis la 6 avait explicitement différée : **une boucle de saison**. Sans
elle, aucune route "avancer le temps" n'avait quoi que ce soit à appeler.

**`src/core/world/` (nouveau)** : `calendrier.py` (`generer_calendrier`,
méthode du cercle, aller-retour), `classement.py` (`calculer_classement`,
départage points/différence de buts/buts pour/confrontation directe —
cette dernière seulement par paire stricte, pas en sous-groupe complet,
voir le docstring du module) et `saison.py` (`initialiser_saison`,
`avancer_un_jour`, `avancer_jusqua_journee` — simule les matches du jour
via `AIController` + `MoteurPossession`, applique fatigue/forme/blessures/
suspensions, journalise).

**`src/api/`** (nouveau, FastAPI + `uvicorn`, ajoutés aux dépendances) :
un état de partie unique en mémoire (`etat_serveur.py`, un `Monde` importé
au démarrage puis muté par la boucle de saison), des vues pydantic
dédiées par écran (`vues.py` — "penser en vues, pas en entités") et cinq
routeurs (`routes_monde.py`, `routes_clubs.py`, `routes_competitions.py`,
`routes_joueurs.py`, `routes_matches.py`). Tous les endpoints listés en
"Endpoints" plus bas sans mention "non implémenté" fonctionnent contre le vrai jeu de données
(32 000 joueurs, 96 clubs actifs) — vérifié à la fois par
`tests/integration/api/` (24 tests, TestClient) et manuellement au
navigateur (clubs, effectif, calendrier, classement, recherche de
joueurs, fiche joueur, compte rendu de match, avancée du temps).

**`web/`** (nouveau) : HTML/CSS/JS vanilla comme spécifié, un routeur par
ancre fait maison (`app.js`), un tableau triable réutilisé partout
(`composants.js`). Couvre Clubs (liste + effectif + calendrier),
Compétitions (liste + classement + calendrier), Recherche de joueurs +
fiche joueur, et le compte rendu de match — pas les cinq écrans en
entier (voir "Non implémenté" plus bas).

**Non implémenté, documenté plutôt que masqué** :

- **Onglets Budget/Historique du club, Statistiques (buteurs/passeurs/notes)
  et le volet "meilleur buteur par saison" de l'Historique de compétition** :
  rien n'agrège de séries temporelles (finances dans le temps, stats de
  match par joueur) — seule la démographie, l'état courant, le palmarès
  par saison et (depuis peu) les transferts effectifs sont suivis. Ajouter
  ces endpoints suppose d'abord l'agrégation correspondante dans
  `core/world`, pas seulement une nouvelle vue.
- **`fin_mercato` sur `POST /api/monde/avancer`** : la boucle de mercato
  tourne désormais (voir "Boucle de mercato" plus haut), mais rien ne
  saute directement à la fin de la fenêtre — seuls `jour`/`journee`
  existent comme granularité d'avancée.
- **Promotion/relégation** : voir "Fin de saison" plus haut — la
  saison se relance bien, mais toujours pour les mêmes clubs.
- **Mode "match en direct"** : `ResultatMatch.evenements` est déjà
  horodaté comme prévu (`docs/architecture.md`), rien ne le rejoue
  progressivement — le front affiche le compte rendu complet d'un coup.

## Contrainte v1

L'utilisateur est **observateur**. Aucun écran n'a de bouton d'action sur un
club : pas de composition à valider, pas d'offre à émettre. L'interface sert à
consulter et à faire avancer le temps.

Cela n'autorise pas à mélanger lecture et décision dans le code : les endpoints
sont déjà organisés pour qu'ajouter le contrôle utilisateur consiste à ajouter
des routes d'action, pas à réécrire les routes de lecture.

## Principes

**Penser en vues, pas en entités.** Un endpoint renvoie exactement ce qu'un écran
affiche, plutôt qu'un REST générique qui obligerait le front à faire quarante
requêtes pour reconstituer une page.

**Filtrage, tri et pagination côté serveur.** Ne jamais renvoyer 32 000 joueurs
au navigateur. Toute liste est paginée, y compris la recherche de joueurs qui
porte sur l'ensemble des clubs, actifs et dormants.

**Code couleur constant.** Gardien, défense, milieu, attaque gardent la même
teinte partout, de la liste d'effectif au terrain. C'est ce qui permet de lire
une composition en une seconde.

**Trois chiffres par ligne de joueur.** Âge, salaire, fin de contrat. Une
échéance à moins de 12 mois passe en rouge. C'est la liste de tâches implicite,
et elle remplace tous les écrans de gestion supprimés.

## Contrôle du temps

Barre persistante en tête d'application :

- Date courante, saison, prochaine échéance
- Boutons : avancer d'un jour, avancer à la prochaine journée de championnat,
  avancer à la fin de la fenêtre de mercato
- Journal des événements du jour : résultats, transferts, blessures

**Avance automatique (2026-09-11, ajouté)** : bouton "▶ Auto" en bascule
play/pause — un clic enchaîne "avancer à la prochaine journée" en boucle
(pause de 900ms entre deux journées, le temps de lire le journal), un
second clic l'arrête. Purement côté `web/app.js`, aucun endpoint dédié :
chaque itération est un appel normal à `POST /api/monde/avancer`. Les
boutons d'avance manuelle sont désactivés pendant que l'auto tourne pour
éviter un chevauchement de requêtes ; le bouton auto lui-même reste
cliquable pour permettre l'arrêt. S'arrête aussi tout seul si un appel
échoue (erreur affichée comme pour un clic manuel).

**Indicateur de fenêtre de mercato (2026-09-11, ajouté)** : pastille
"● Mercato ouvert" / "○ Mercato fermé" à côté de la date, dérivée de
`core.world.mercato.fenetre_mercato_ouverte(monde.date, cfg)` — même
fonction pure que celle qui décide si `avancer_un_jour` doit jouer un
tour de mercato, exposée en plus dans `GET /api/monde/etat` (nouveau
champ `mercato_ouvert`) pour ne pas dupliquer la logique été/hiver côté
front. Se met à jour à chaque avancée du temps, y compris pendant
l'avance automatique.

## Écrans

### Club

| Onglet | Contenu |
|---|---|
| Effectif | liste triable : poste, nom, âge, note, salaire, fin de contrat, état (blessé, suspendu, fatigue) |
| Calendrier | matches passés et à venir, résultat, adversaire, domicile/extérieur |
| Budget | budget de transfert, masse salariale et plafond, solde, revenus |
| Transferts | arrivées et départs de la saison, avec montants |
| Historique | classements passés, palmarès, transferts marquants |

En-tête : nom, pays, compétition, réputation, classement actuel, forme sur les
5 derniers matches, nombre de joueurs sous contrat, masse salariale actuelle
(€/semaine) et budget transferts (2026-09-11, ajouté — pas le plafond
salarial ni le solde, qui restent réservés à l'onglet Budget, non
implémenté). Les trois mêmes chiffres apparaissent aussi comme colonnes
de la liste des clubs, pour comparer d'un coup d'œil sans ouvrir chaque
fiche. `GET /api/clubs` agrège `nb_joueurs_sous_contrat`/`masse_salariale`
par club en un seul passage sur les ~32 000 joueurs
(`core.ai.budgets.effectifs_par_club`) avant pagination, plutôt que de
refiltrer l'effectif de chaque club un par un (`O(clubs)` au lieu de
`O(clubs × joueurs)`) — `budget_transfert` est en revanche un attribut
direct de `Club`, pas d'agrégation nécessaire.

### Compétition

| Onglet | Contenu |
|---|---|
| Classement | position, J, V, N, D, BP, BC, différence, points, forme |
| Calendrier | matches par journée, avec résultats |
| Statistiques | meilleurs buteurs, passeurs, meilleures notes moyennes, clean sheets, cartons |
| Historique | champions par saison, meilleur buteur par saison |

### Joueur

| Section | Contenu |
|---|---|
| Identité | nom, nationalité, âge, date de naissance, poste, postes secondaires |
| Caractéristiques | les 13 attributs, groupés par famille, avec barres |
| Potentiel | **fourchette d'estimation**, jamais la valeur réelle |
| État | blessure en cours et durée, fatigue, suspension, forme, moral |
| Contrat | club, salaire hebdomadaire, date de fin, valeur de marché estimée |
| Saison en cours | matches, minutes, buts, passes, note moyenne, cartons |
| Historique | une ligne par saison ; transferts avec montants ; courbe de la note globale par saison |

### Match

Écran de compte rendu, consultable après simulation :

- Score, compétition, journée, stade
- xG, tirs, possession, corners, cartons
- Fil chronologique des événements avec joueurs nommés
- Compositions des deux équipes avec notes individuelles

En v1 le match est simulé instantanément. Prévoir dès la conception que le
`ResultatMatch` contient tous les événements horodatés : le mode « match en
direct » se construira en rejouant ce fil, sans toucher au moteur.

### Recherche de joueurs

Vue transversale sur les 32 000 joueurs. Filtres serveur : poste, âge, niveau,
nationalité, club, statut du club (actif ou dormant), fourchette de salaire,
statut contractuel. Tri sur toute colonne, pagination obligatoire.

### Transferts (2026-09-11, ajouté)

Vue transversale sur `Monde.historique.transferts`, tous clubs et toutes
saisons confondus — pendant du sous-onglet "Transferts" de la fiche club
(qui reste filtré sur un seul club), accessible directement depuis le
menu principal. Colonnes : date, joueur, club d'origine, club de
destination, montant, saison. Triable sur toute colonne (date décroissante
par défaut), pagination serveur, filtre par saison. `GET
/api/monde/transferts` accepte aussi `club=` (non exposé dans ce filtre
de menu — déjà couvert par `GET /api/clubs/{id}/transferts`).

Un club dormant est consultable — nom, effectif, fiches joueurs — mais n'a ni
classement, ni calendrier, ni statistiques de saison. L'interface doit le
signaler explicitement plutôt que d'afficher des sections vides.

## Endpoints

Implémentés sauf mention contraire (voir "État de l'implémentation" plus haut) :

```
GET  /api/monde/etat                     date, saison, prochaines échéances, mercato_ouvert
POST /api/monde/avancer                  {jusqu_a: "jour" | "journee"}          — pas de "fin_mercato"
GET  /api/monde/journal?date=             dernier journal produit             — pas de filtre par date
GET  /api/monde/transferts?saison=&club=&page=   tous les transferts, paginé

GET  /api/clubs?competition=&statut=actif|dormant&recherche=&page=&tri=
GET  /api/clubs/{id}                      en-tête + résumé
GET  /api/clubs/{id}/effectif
GET  /api/clubs/{id}/calendrier
GET  /api/clubs/{id}/finances             — non implémenté
GET  /api/clubs/{id}/transferts?saison=
GET  /api/clubs/{id}/historique           — non implémenté

GET  /api/competitions
GET  /api/competitions/{id}/classement
GET  /api/competitions/{id}/calendrier?journee=
GET  /api/competitions/{id}/statistiques?type=buteurs|passeurs|notes   — non implémenté
GET  /api/competitions/{id}/historique    champion + classement final par saison — pas de buteur/passeur

GET  /api/joueurs?poste=&age_min=&age_max=&niveau_min=&nation=&club=&statut_club=&page=&tri=
GET  /api/joueurs/{id}
GET  /api/joueurs/{id}/historique         — non implémenté

GET  /api/matches/{id}                    compte rendu complet

POST /api/partie/sauvegarder              {slot: str}
POST /api/partie/charger                  {slot: str}
GET  /api/partie/slots
```

## Front

HTML, CSS et JS vanilla. L'essentiel des écrans est constitué de tableaux
triables — un framework n'apporterait rien ici.

- Une page par écran, navigation par ancres ou petit routeur maison
- Aucun état applicatif dupliqué côté client : le serveur est la source de vérité
- Rafraîchir après chaque avancée de temps

Compter environ la moitié du temps total du projet sur l'interface si l'on veut
quelque chose d'agréable à utiliser. Ne pas commencer avant que le harnais de
calibrage donne des résultats corrects.
