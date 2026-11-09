# Serpentix

Projet NSI : **site web dynamique avec base de données SQL** + jeu navigateur
en 1 contre 1 (mélange de *Snake* et de *Slither.io*).

- Interface **noir & blanc** uniquement ; les seules couleurs sont les **skins**
  du serpent (rouge, vert, orange, jaune), achetés avec des **coins** gagnés en jouant.
- Mode **solo** (pour gagner des coins) ou **duel 1v1 en temps réel** : on crée une
  salle, on envoie le code à 6 caractères à un ami, il le tape et la partie démarre.

## Fonctionnalités

| Fonction | Où | Exigence NSI |
|---|---|---|
| Inscription, connexion, déconnexion (mots de passe hachés) | `/inscription`, `/connexion` | formulaire → BDD |
| Gestion des joueurs : créer, lister, voir, modifier, supprimer | `/utilisateurs` (lien en pied de page) | CRUD complet |
| Validation des formulaires dans le navigateur **et** sur le serveur | `validation.js` + `valider_*()` dans `app.py` | sécurité client + serveur |
| Menu de navigation sur toutes les pages | `templates/base.html` | menu |
| Boutique de skins (achat / équipement) | `/boutique` | mise à jour BDD |
| Classement calculé en SQL (jointures, agrégats) | `/classement` | affichage collectif |
| Solo dans le navigateur | `/solo` | JavaScript |
| 1v1 temps réel avec Socket.IO | `/jouer` puis `/partie/<code>` | Python serveur |
| Bonus turbo △ et bouclier ○ | moteur `game_engine.py` | algorithmique |
| Contrôles clavier, glisser du doigt et flèches tactiles | `controles.js` | |

## Règles du jeu

- Manger une pomme : **+1 point**, le serpent grandit d’une case.
- Mur, son propre corps ou le **corps adverse** : éliminé.
- **Tête contre tête** : le plus long gagne (égalité = match nul).
- **Turbo △** : 2 cases par tour pendant 3 s. **Bouclier ○** : annule un choc,
  le serpent recule et tourne vers une case libre.
- Compte à rebours de 3 s avant chaque départ. Pause avec Espace en solo.
- Coins : solo = 1 par pomme (80 max par partie) ; 1v1 = score + **15** si victoire.

## Installation et lancement

```bash
git clone https://github.com/Dontbyshai/Serpentix.git
cd Serpentix
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Puis ouvrir <http://127.0.0.1:5000>. La base `serpentix.db` est créée
automatiquement au premier lancement à partir de `schema.sql`.

Variables d’environnement facultatives : `SERPENTIX_PORT` (5000 par défaut),
`SERPENTIX_HOST` (0.0.0.0), `SERPENTIX_SECRET_KEY` (sinon une clé aléatoire est
générée dans `.secret_key`, fichier ignoré par git).

### Comptes de démonstration

Créés seulement si la base est vide :

| Pseudo | Mot de passe | Coins de départ |
|---|---|---|
| `joueur1` | `joueur123` | 100 |
| `joueur2` | `joueur2123` | 100 |

### Tester le 1v1 sur un seul ordinateur

1. Fenêtre normale : `joueur1` → **Jouer** → **Générer un code** → **Entrer dans la salle**.
2. Fenêtre de navigation privée : `joueur2` → **Jouer** → taper le code → **Rejoindre**.
3. La partie démarre après un compte à rebours de 3 s.

Le même compte ne peut pas jouer contre lui-même dans deux onglets.

### Tests automatiques

```bash
python -m unittest discover tests
```

12 tests vérifient les règles du moteur (murs, corps adverse, tête contre tête,
bouclier, turbo, pommes, forfait, codes de salle…).

## Architecture

```
navigateur (HTML/CSS/JS) ──HTTP──▶ Flask (app.py) ──SQL──▶ SQLite (serpentix.db)
          ▲                              │
          └──── Socket.IO (WebSocket) ◀──┘  moteur du 1v1 (game_engine.py)
```

```
serpentix/
├── app.py              # serveur Flask : routes, validation, sessions, Socket.IO
├── database.py         # TOUTES les requêtes SQL (CRUD, coins, parties, classement)
├── game_engine.py      # règles du jeu 1v1 (sans Flask ni SQL)
├── schema.sql          # création des tables
├── requirements.txt    # dépendances Python
├── tests/              # tests unittest du moteur
├── templates/          # pages HTML (Jinja)
├── static/css/         # style.css
├── static/js/          # validation, lobby, solo, 1v1, dessin, contrôles, décor
└── docs/               # présentation, schéma BDD, architecture, améliorations
```

Détails : [docs/architecture.md](docs/architecture.md) ·
[docs/schema.md](docs/schema.md) ·
[docs/presentation.md](docs/presentation.md) ·
[docs/ameliorations.md](docs/ameliorations.md)

## Sécurité (résumé)

- Requêtes SQL **paramétrées** (`?`) : pas d’injection SQL.
- Mots de passe **hachés** (Werkzeug), jamais stockés en clair.
- Jeton **CSRF** sur tous les formulaires et appels `fetch` en POST.
- Échappement automatique Jinja + `textContent` en JS : pas d’injection HTML (XSS).
- Chacun ne peut modifier ou supprimer que **son** compte (vérifié côté serveur).
- Coins du solo **vérifiés par le serveur** (partie commencée, payée une seule fois,
  score plausible pour la durée).

## Auteur

Projet réalisé par **Shaï** (NSI).

## Licence

Projet scolaire, usage libre pour démonstration éducative.
