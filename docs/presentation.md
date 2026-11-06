# Document de présentation — Serpentix

**Projet NSI : création d’un site web dynamique avec base de données**

---

## 1. Participants

| Nom | Rôle |
|-----|------|
| **Shaï** | Conception, développement (Flask, SQL, HTML/CSS/JS, jeu), documentation, oral |

Projet réalisé de façon autonome (équipe d’un élève).

---

## 2. Description du site

**Serpentix** est un site web collaboratif qui permet :

1. De gérer des **comptes joueurs** (inscription, connexion, profil, liste admin).
2. De **jouer en 1 contre 1** dans le navigateur à un mélange de Snake et Slither.io :
   - grandir en mangeant des pommes ;
   - éliminer l’adversaire en touchant son corps ;
   - bonus *turbo* (vitesse) et *bouclier* (1 choc absorbé) ;
   - couleur de serpent personnalisable.
3. De consulter un **classement** alimenté par la base SQL.

Le serveur web est simulé en **Python (Flask)**. La communication temps réel du jeu utilise **Flask-SocketIO** (WebSocket). La base est en **SQLite** (langage SQL).

---

## 3. Fonctionnalités proposées

| Page | Contenu |
|------|---------|
| Accueil | Présentation, règles, accès rapide |
| Inscription / Connexion | Formulaires sécurisés (client + serveur) |
| Joueurs | CRUD utilisateurs (liste, détail, créer, modifier, supprimer) |
| Profil | Couleur de skin, e-mail, mot de passe, historique |
| Jouer (lobby) | Créer / rejoindre une salle par code |
| Partie | Canvas 1v1 temps réel |
| Solo | Entraînement local |
| Classement | Victoires et scores depuis la BDD |

Menu de navigation présent sur **toutes** les pages.

---

## 4. Liste des tâches & répartition

Comme le projet est mené par un seul élève, toutes les tâches lui sont attribuées.

| # | Tâche | Statut |
|---|-------|--------|
| 1 | Cahier des charges & règles du jeu | Fait |
| 2 | Schéma SQL (3 tables, clés, index) | Fait |
| 3 | Module `database.py` (CRUD) | Fait |
| 4 | Routes Flask + templates + CSS | Fait |
| 5 | Validation JS + validation Python | Fait |
| 6 | Auth session + hash mots de passe | Fait |
| 7 | Moteur de jeu (`game_engine.py`) | Fait |
| 8 | Lobby + SocketIO + canvas client | Fait |
| 9 | Mode solo | Fait |
| 10 | Classement / sauvegarde des scores | Fait |
| 11 | Documentation (README, schéma, oral) | Fait |
| 12 | Dépôt GitHub public | Fait |

---

## 5. Calendrier prévisionnel (indicatif)

| Semaine | Objectif |
|---------|----------|
| S1 | Thématique, cahier des charges, schéma BDD |
| S2 | Flask + CRUD utilisateurs + formulaires |
| S3 | Auth, profil, skins, pages marketing |
| S4 | Moteur de jeu + canvas solo |
| S5 | Lobby, SocketIO, 1v1, scores |
| S6 | Polish, documentation, préparation oral |

*(Dates à adapter selon le calendrier de la classe.)*

---

## 6. Structure de la base de données

Voir **`docs/schema.md`** et **`schema.sql`**.

Résumé :

- `utilisateurs` — comptes
- `parties` — salles de jeu
- `participations` — scores (association N–N)

---

## 7. Historique & problèmes rencontrés

| Problème | Solution |
|----------|----------|
| Besoin de 2 joueurs pour tester le 1v1 | Mode solo + comptes démo `admin` / `joueur2` ; tester avec 2 onglets |
| Demi-tour du serpent trop facile | Interdiction côté moteur (`changer_direction`) |
| Collision tête-à-tête ambiguë | Les deux serpents meurent → match nul possible |
| Mot de passe en clair = interdit | Hash Werkzeug (`generate_password_hash` / `check_password_hash`) |
| Injection SQL | Requêtes paramétrées uniquement |
| Boucle de jeu bloquante | Thread daemon + `socketio.emit` hors du lock |
| Validation JS contournable | Double contrôle systématique en Python |

---

## 8. Compétences acquises (lien programme)

- Modéliser un problème (flux joueur ↔ serveur ↔ BDD)
- Décomposer (auth / CRUD / moteur / rendu canvas)
- Traduire un algorithme (collisions, tick de jeu) en Python et JS
- Acquisition / mémorisation / diffusion d’informations (formulaires → SQL → pages)
- Autonomie et créativité (jeu temps réel au-delà du CRUD minimal)

---

## 9. Prolongements possibles

- Chat texte dans la salle
- Matchmaking automatique (file d’attente)
- Tournoi / saison avec reset de classement
- Plus de skins (motifs, accessoires)
- Hébergement en ligne (Railway, PythonAnywhere…)
- Remplacer SQLite par PostgreSQL pour plus de joueurs simultanés
- Replays ou spectateurs

---

## 10. Codes réalisés

L’ensemble du code source est dans le dépôt GitHub, notamment :

- `app.py` — serveur et routes
- `database.py` — SQL
- `game_engine.py` — logique de jeu
- `templates/` — HTML
- `static/js/` — validation, lobby, jeu
- `static/css/style.css` — apparence

Tous les fichiers sont **commentés en français**.


## Refonte UX (v2)

- Landing jeu noir & blanc + bouton Jouer
- Boutique skins (rouge / vert / orange / jaune) contre coins
- Modes Solo et 1v1 par code partageable
- Panneau admin retiré du menu ; CRUD NSI reste en pied de page
