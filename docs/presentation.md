# Document de présentation : Serpentix

**Projet NSI : création d’un site web dynamique avec base de données**

---

## 1. Participants

| Nom | Rôle |
|---|---|
| **Shaï** | Conception, base de données, serveur Flask, pages HTML/CSS/JS, jeu, tests, documentation, oral |

Projet mené seul : toutes les tâches ci-dessous sont attribuées à Shaï.

---

## 2. Description du site

**Serpentix** est un jeu de serpent jouable dans le navigateur, entre Snake et
Slither.io, avec un vrai site autour :

1. **comptes joueurs** stockés dans une base SQLite (inscription, connexion,
   profil, gestion complète des joueurs) ;
2. **parties en temps réel à 2 ou 3 joueurs** : un joueur crée une salle en
   choisissant 2 ou 3 joueurs, envoie le code à 6 caractères à ses amis, et la
   partie démarre quand la salle est pleine. Le dernier serpent en vie gagne ;
   six bonus (turbo, bouclier, fantôme, aimant, ciseaux, gel) ;
3. **mode solo** pour s’entraîner et gagner des **coins** ;
4. **boutique** : les coins débloquent des couleurs de serpent (rouge, vert,
   orange, jaune) ; tout le reste du site est en noir et blanc ;
5. **classement** calculé en SQL à partir des parties enregistrées : podium,
   tri par victoires, % de victoires, meilleur score ou coins, statistiques
   par joueur (parties, victoires, nuls, défaites).

Le serveur web est écrit en **Python avec Flask**, le temps réel utilise
**Flask-SocketIO** (WebSocket), la base est **SQLite** (langage SQL) et
l’interface est en **HTML, CSS et JavaScript** (canvas).

---

## 3. Fonctionnalités et lien avec le cahier des charges

| Exigence du sujet | Réalisation |
|---|---|
| Formulaire qui ajoute des données en base | `/inscription` et `/utilisateurs/nouveau` → `INSERT INTO utilisateurs` |
| Formulaires sécurisés côté client | `validation.js` + attributs HTML (`minlength`, `pattern`, `required`) |
| Sécurité côté serveur | fonctions `valider_*` en Python, unicité, droits « seulement son compte », jeton CSRF, requêtes paramétrées |
| Affichage individuel et collectif | `/utilisateurs/<id>` (fiche) et `/utilisateurs` (tableau), `/classement` |
| Bouton supprimer | « Supprimer » (POST + confirmation) → `DELETE FROM utilisateurs` |
| Bouton mettre à jour | « Modifier » et `/profil` → `UPDATE utilisateurs` |
| Menu de navigation | en-tête de `base.html`, présent sur toutes les pages (menu ☰ sur mobile) |
| Codes commentés | chaque fichier Python, JS, CSS et HTML est commenté en français |

Pages du site :

| Page | Contenu |
|---|---|
| Accueil | Arène animée en fond, présentation, bouton **Jouer**, liste des bonus |
| Inscription / Connexion | Formulaires validés client + serveur |
| Jouer | Choix solo ou multijoueur, créer une salle (2 ou 3) / rejoindre |
| Partie | Plateau temps réel à 2 ou 3, scores, effets actifs, compte à rebours, écran de fin animé |
| Solo | Plateau solo, pause, effets actifs, écran de fin |
| Boutique | Achat et équipement des skins |
| Classement | Podium, tri, victoires / nuls / défaites, % de victoires, meilleur score, coins |
| Profil | E-mail, mot de passe, historique |
| Gestion joueurs | CRUD complet (lien en pied de page) |

---

## 4. Liste des tâches

| # | Tâche | Statut |
|---|---|---|
| 1 | Choix du thème, règles du jeu, cahier des charges | Fait |
| 2 | Modélisation de la base (3 tables, clés, index) et `schema.sql` | Fait |
| 3 | Module `database.py` (CRUD, coins, parties, classement) | Fait |
| 4 | Serveur Flask : routes, templates, sessions | Fait |
| 5 | Validation des formulaires en JS et en Python | Fait |
| 6 | Mots de passe hachés, protection CSRF, droits par compte | Fait |
| 7 | Moteur du jeu (`game_engine.py`) | Fait |
| 8 | Salles 1v1 avec Socket.IO, lobby par code | Fait |
| 9 | Mode solo et crédit des coins vérifié | Fait |
| 10 | Boutique de skins, classement, historique | Fait |
| 11 | Design noir et blanc, version mobile (glisser, flèches) | Fait |
| 12 | Tests automatiques du moteur (`tests/`) | Fait |
| 13 | Documentation (README, schéma, architecture, améliorations) | Fait |
| 14 | Mise en ligne sur un serveur et dépôt GitHub | Fait |
| 15 | Ralentir le jeu (une seule constante de vitesse) | Fait |
| 16 | Parties à 3 joueurs (BDD, moteur, lobby) | Fait |
| 17 | Quatre nouveaux bonus + minuteurs dans le HUD | Fait |
| 18 | Écrans de fin animés, classement avec podium et tri | Fait |
| 19 | Arène animée sur l’accueil, page bloquée pendant le jeu | Fait |
| 20 | Préparation de l’oral | À faire |

---

## 5. Calendrier prévisionnel

| Semaine | Objectif |
|---|---|
| S1 | Thème, cahier des charges, schéma de la base |
| S2 | Flask + CRUD utilisateurs + formulaires et validation |
| S3 | Connexion, profil, boutique, classement |
| S4 | Moteur de jeu et mode solo |
| S5 | Salles 1v1 temps réel, sauvegarde des scores |
| S6 | Design, mobile, sécurité, tests, documentation, oral |

*(Calendrier à mettre à jour selon les dates de la classe.)*

---

## 6. Structure de la base de données

Voir **[schema.md](schema.md)** (diagramme, tables, requêtes) et `schema.sql`.

- `utilisateurs` : les comptes (pseudo, e-mail, hash, skin, coins) ;
- `parties` : les salles (code, statut, nombre de joueurs 2 ou 3, créateur, vainqueur) ;
- `participations` : qui a joué quelle partie, avec quel score (table d’association).

Le fonctionnement complet (routes, événements temps réel, flux des données)
est décrit dans **[architecture.md](architecture.md)**.

---

## 7. Historique de la réalisation

| Version | Contenu |
|---|---|
| v1 | Base SQLite, CRUD utilisateurs, connexion, premier jeu 1v1 avec Socket.IO, lobby |
| v2 | Refonte « jeu » : accueil avec bouton Jouer, mode solo, coins, boutique de skins, suppression du compte admin du menu |
| v3 | Mise en ligne sur un serveur (port configurable) |
| v4 | Interface strictement noir et blanc, serpent animé en fond |
| v5 | Audit complet : corrections de bugs, sécurité (CSRF, anti-triche), contrôles mobiles, compte à rebours, tests, commentaires et documentation |
| v6 | Jeu ralenti (7 pas/s), parties à 3, 4 nouveaux bonus, écrans de fin animés, classement avec podium et tri, arène animée sur l’accueil, page bloquée pendant le jeu, comptes Shai / zoubida / noah |

---

## 8. Problèmes rencontrés et solutions

| Problème | Solution |
|---|---|
| Il faut deux joueurs pour tester le 1v1 | Deux comptes de démonstration + une fenêtre normale et une fenêtre privée ; tests automatiques du moteur |
| Supprimer un joueur qui avait déjà joué provoquait une erreur 500 (clé étrangère `parties.createur_id`) | `supprimer_utilisateur` efface d’abord le lien vainqueur, puis ses parties, puis le joueur, dans une transaction ; `ON DELETE CASCADE / SET NULL` ajoutés au schéma |
| N’importe qui pouvait s’ajouter 80 coins en appelant `/api/solo/fin` à la main | Le serveur note le début de la partie dans sa mémoire, ne paie qu’une fois et plafonne le score selon la durée réelle |
| Un même compte pouvait jouer contre lui-même dans deux onglets (coins gratuits) | Le moteur refuse un 2e serpent pour le même compte (et remplace la connexion si on recharge la page) |
| Les serpents partaient face à face sur la même ligne : match nul en 3 s si personne ne bougeait | Départs en diagonale + compte à rebours de 3 s |
| Le bouclier ne servait à rien : le serpent repartait dans le même mur au tour suivant | Le bouclier annule le pas et fait tourner le serpent vers une case libre |
| En turbo, un serpent pouvait « sauter » par-dessus un corps | Collisions vérifiées après chaque case, pas seulement à la fin du tour |
| Deux touches rapides : le premier virage était perdu | File de 2 virages par serpent |
| Joueur qui quitte : partie jamais clôturée en base, gagnant non payé | `cloturer_partie()` enregistre le forfait et libère la mémoire |
| Recharger la page d’attente détruisait la salle | La salle est recréée depuis la base tant qu’elle est « en attente » |
| Formulaires envoyables depuis un autre site (CSRF) | Jeton secret dans chaque formulaire et chaque `fetch`, vérifié avant chaque POST |
| Redirection après connexion vers n’importe quel site (`?next=`) | Seuls les chemins internes (`/…`) sont acceptés |
| Gains de coins simultanés qui pouvaient s’écraser | `UPDATE … SET coins = coins + ?` calculé par SQLite |
| Validation JavaScript contournable | Toutes les règles sont revérifiées en Python |
| Mot de passe en clair interdit | Hash Werkzeug (`generate_password_hash` / `check_password_hash`) |
| Injection SQL | Requêtes paramétrées uniquement (`?`) |
| Pas jouable sur téléphone | Glisser du doigt + flèches à l’écran (`controles.js`) |
| Gris dans l’interface (transparence) | Dessin uniquement en `#000` / `#fff`, contours au lieu de transparence |
| Le jeu était trop rapide, et la vitesse était recopiée à plusieurs endroits (Python et JS) | Une seule constante `TICKS_PAR_SECONDE` ; toutes les durées sont en secondes converties par `secondes()` ; le solo reçoit les réglages du serveur |
| À 3 joueurs, la règle « tête contre tête » ne marchait que pour une paire | Test de **chaque paire** de serpents ; à 3 sur la même case, seul le plus long survit |
| Un joueur qui quittait la salle d’attente puis un nouvel arrivant pouvaient avoir la même case de départ | Les places sont données au démarrage, d’après l’ordre final des joueurs |
| Départs à 3 : risque qu’un joueur soit avantagé | Trois colonnes parallèles, même distance au mur pour chacun (vérifié par un test) |
| Les mots de passe `1234` demandés pour 3 comptes sont plus courts que la règle du formulaire (6 caractères) | Les comptes sont créés directement par le serveur (`python app.py --comptes`) ; la règle reste pour les inscriptions |
| Le tri du classement vient de l’URL : risque d’injection SQL | Liste blanche `TRIS_CLASSEMENT` : on choisit une clause `ORDER BY` connue, jamais le texte reçu |
| Ancienne base sans la colonne `nb_joueurs` | `migrer_si_besoin()` fait `ALTER TABLE parties ADD COLUMN` sans perdre de données |
| La page défilait avec la molette ou les flèches pendant la partie | Page en `100vh` sans débordement + `preventDefault()` sur molette, doigt et touches (`passive: false`) |
| Le serpent décoratif de l’accueil ressemblait à quelques carrés perdus | Arène plein écran avec plusieurs serpents automatiques (pommes, collisions, réapparition), textes sur panneaux noirs pleins |

---

## 9. Compétences mobilisées

- **Analyser et modéliser** : flux navigateur ↔ Flask ↔ SQLite, et navigateur ↔
  Socket.IO pour le temps réel.
- **Décomposer** : `app.py` (web), `database.py` (SQL), `game_engine.py` (règles)
  séparés ; `dessin.js`, `controles.js` et `fin.js` réutilisés par le solo et le
  multijoueur.
- **Traduire des algorithmes** : déplacement par file (tête ajoutée, queue
  retirée), détection de collisions par paires, règle tête contre tête, aimant
  (distance de Manhattan), ennemi le plus proche, tirage pondéré des bonus,
  algorithme glouton des serpents de l’arène, particules (vitesse + gravité).
- **Valider** : tests `unittest` du moteur, tests manuels des pages et du CRUD.
- **Informations** : acquisition (formulaires), mémorisation (SQL), traitement
  (Python), diffusion (pages HTML, WebSocket).
- **Autonomie et créativité** : jeu temps réel au-delà du CRUD demandé.

---

## 10. Prolongements possibles

Liste détaillée et classée : **[ameliorations.md](ameliorations.md)**.
Principales idées : bouton revanche, meilleur score solo en base, limite des
essais de connexion, file d’attente automatique, mode spectateur, rang
d’élimination dans les parties à 3, table `skins` normalisée.

---

## 11. Codes réalisés

Tout le code est dans le dépôt GitHub :

- `app.py` : serveur, routes, validation, Socket.IO
- `database.py` : toutes les requêtes SQL
- `game_engine.py` : règles du jeu
- `schema.sql` : création des tables
- `templates/` : pages HTML (Jinja)
- `static/css/style.css` : apparence
- `static/js/` : validation, lobby, solo, partie, dessin, contrôles, écrans de fin, arène
- `tests/test_game_engine.py` : tests automatiques

Tous les fichiers sont commentés en français.
