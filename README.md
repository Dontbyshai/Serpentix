# Serpentix

Projet NSI — **site web dynamique avec base de données** + jeu navigateur **1 contre 1**
(mélange de *Snake* et *Slither.io*).

Mange des pommes pour grandir, élimine l’adversaire en touchant son corps.
Pas de lasers façon Tron. Skins (couleur) + bonus turbo / bouclier.

## Fonctionnalités

- Inscription / connexion (session Flask, mots de passe hachés avec Werkzeug)
- **CRUD utilisateurs** complet (créer, lister, voir, modifier, supprimer)
- Validation des formulaires **côté client (JS)** et **côté serveur (Python)**
- Menu de navigation sur toutes les pages
- Lobby : créer / rejoindre une salle par code
- Jeu 1v1 temps réel (Flask-SocketIO + canvas)
- Mode solo d’entraînement
- Classement (victoires / scores stockés en SQLite)
- Profil : choix de la couleur du serpent

## Stack

| Couche | Techno |
|--------|--------|
| Serveur | Python 3, Flask, Flask-SocketIO |
| Base de données | SQLite (`schema.sql`) |
| Front | HTML, CSS, JavaScript (canvas) |

## Installation & lancement

```bash
# 1. Cloner
git clone https://github.com/Dontbyshai/Serpentix.git
cd Serpentix

# 2. Environnement virtuel
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt

# 3. Lancer
python app.py
```

Ouvre ensuite [http://127.0.0.1:5000](http://127.0.0.1:5000).

La base `serpentix.db` est créée automatiquement au premier lancement
(à partir de `schema.sql`).

### Comptes de démonstration

Au premier démarrage (base vide), deux comptes sont créés :

| Pseudo   | Mot de passe | Rôle  |
|----------|--------------|-------|
| `admin`  | `admin123`   | Admin |
| `joueur2`| `joueur2123` | Joueur|

Change ces mots de passe après la démo.

### Tester le 1v1 sur une seule machine

1. Onglet A : connexion `admin` → Jouer → Créer une salle (noter le code)
2. Onglet B (navigation privée) : connexion `joueur2` → Rejoindre avec le code
3. La partie démarre dès que les 2 joueurs sont dans la salle

## Structure du dépôt

```
serpentix/
├── app.py                 # Serveur Flask + routes + SocketIO
├── database.py            # Accès SQLite (CRUD, scores)
├── game_engine.py         # Moteur de jeu (serpents, collisions, bonus)
├── schema.sql             # Schéma SQL
├── requirements.txt
├── README.md
├── docs/
│   ├── schema.md          # Schéma BDD + diagramme Mermaid
│   └── presentation.md    # Document de présentation (oral NSI)
├── templates/             # Pages Jinja2
└── static/
    ├── css/style.css
    └── js/                # validation, lobby, game, solo
```

## Sécurité (niveau NSI)

- Mots de passe **hachés** (jamais en clair)
- Requêtes SQL **paramétrées** (anti injection)
- Validation serveur systématique (même si le JS est contourné)
- `SECRET_KEY` configurable via la variable d’environnement `SERPENTIX_SECRET_KEY`
  (valeur de dev fournie — **à changer en production**)

## Auteur

Projet réalisé par **Shaï** dans le cadre de l’enseignement de NSI.

## Licence

Projet scolaire — usage libre pour démonstration éducative.
