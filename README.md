# Serpentix

Projet NSI : **site web dynamique avec base de données SQL** + jeu navigateur
multijoueur à **2 ou 3 joueurs** (mélange de *Snake* et de *Slither.io*).

- Interface **noir & blanc** uniquement ; les seules couleurs sont les **skins**
  du serpent (rouge, vert, orange, jaune), achetés avec des **coins** gagnés en jouant.
- Mode **solo** (pour gagner des coins) ou **partie en temps réel à 2 ou 3** :
  on crée une salle en choisissant 2 ou 3 joueurs, on envoie le code à 6
  caractères, et la partie démarre dès que la salle est pleine.

## Fonctionnalités

| Fonction | Où | Exigence NSI |
|---|---|---|
| Inscription, connexion, déconnexion (mots de passe hachés) | `/inscription`, `/connexion` | formulaire → BDD |
| Gestion des joueurs : créer, lister, voir, modifier, supprimer | `/utilisateurs` (lien en pied de page) | CRUD complet |
| Validation des formulaires dans le navigateur **et** sur le serveur | `validation.js` + `valider_*()` dans `app.py` | sécurité client + serveur |
| Menu de navigation sur toutes les pages | `templates/base.html` | menu |
| Boutique de skins (achat / équipement) | `/boutique` | mise à jour BDD |
| Classement : podium, tri (victoires, % victoires, meilleur score, coins), stats par joueur | `/classement?tri=…` | affichage collectif, SQL |
| Solo dans le navigateur | `/solo` | JavaScript |
| Parties à 2 ou 3 en temps réel avec Socket.IO | `/jouer` puis `/partie/<code>` | Python serveur |
| 6 bonus : turbo, bouclier, fantôme, aimant, ciseaux, gel | moteur `game_engine.py`, [docs/bonus.md](docs/bonus.md) | algorithmique |
| Écrans de fin animés (victoire, défaite, nul) | `fin.js` | canvas + CSS |
| Arène animée (serpents automatiques) derrière l’accueil et la page Jouer | `bg-snake.js` | algorithme glouton |
| Contrôles clavier, glisser du doigt et flèches tactiles ; page bloquée pendant le jeu | `controles.js` | |

## Règles du jeu

- Vitesse : **7 pas par seconde** (constante `TICKS_PAR_SECONDE` dans
  `game_engine.py` ; avant c’était 10). Tout le reste en découle.
- Manger une pomme : **+1 point**, le serpent grandit d’une case.
- Mur, son propre corps ou le **corps d’un adversaire** : éliminé. Le serpent
  éliminé lâche des pommes là où était son corps (si la partie continue).
- **Tête contre tête** : le plus long survit, à égalité les deux sont éliminés.
  À 3 sur la même case, seul le plus long (s’il est seul à l’être) survit.
- **Le dernier serpent en vie gagne.** Si les derniers meurent au même moment : match nul.
- À 3 joueurs, départs équitables : trois colonnes espacées de 10 cases,
  sens alternés, même distance jusqu’au mur pour chacun.
- **6 bonus** (détails dans [docs/bonus.md](docs/bonus.md)) : turbo (2 × plus
  vite, 3 s), bouclier (annule un choc), fantôme (traverse les corps, 4 s),
  aimant (attire les pommes, 6 s), ciseaux (coupe la moitié de la queue de
  l’ennemi le plus proche), gel (ralentit les adversaires, 3 s).
- Compte à rebours de 3 s avant chaque départ. Pause avec Espace en solo.
- Coins : solo = 1 par pomme (80 max par partie) ; multijoueur = score de
  chaque joueur + **15** pour le vainqueur.

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
| `Shai` | `1234` | 100 |
| `noah` | `1234` | 100 |

Sur une base qui existe déjà, `python app.py --comptes` ajoute `Shai`
et `noah` s’ils n’existent pas (rien n’est effacé). Ces comptes
sont créés directement par le serveur : la règle « 6 caractères minimum » reste
appliquée aux inscriptions faites avec le formulaire.

### Tester une partie à 2 ou 3 sur un seul ordinateur

1. Navigateur 1 : `Shai` → **Jouer** → choisir **3 joueurs** → **Générer un code** → **Entrer dans la salle**.
2. Navigateurs 2 et 3 (fenêtre privée, autre navigateur) : `noah`, puis un compte créé avec **S’inscrire** → **Jouer** → taper le code → **Rejoindre**.
3. La partie démarre quand la salle est pleine, après un compte à rebours de 3 s.

Le même compte ne peut pas jouer contre lui-même dans deux onglets.

### Tests automatiques

```bash
python -m unittest discover tests
```

31 tests vérifient les règles du moteur : vitesse, murs, corps adverse, tête
contre tête (à 2 et à 3), départs équitables à 3, dernier survivant, match nul,
forfait, les 6 bonus, codes de salle…

## Architecture

```
navigateur (HTML/CSS/JS) ──HTTP──▶ Flask (app.py) ──SQL──▶ SQLite (serpentix.db)
          ▲                              │
          └──── Socket.IO (WebSocket) ◀──┘  moteur du jeu (game_engine.py)
```

```
serpentix/
├── app.py              # serveur Flask : routes, validation, sessions, Socket.IO
├── database.py         # TOUTES les requêtes SQL (CRUD, coins, parties, classement)
├── game_engine.py      # règles du jeu à 2 ou 3 (sans Flask ni SQL)
├── schema.sql          # création des tables
├── requirements.txt    # dépendances Python
├── tests/              # tests unittest du moteur
├── templates/          # pages HTML (Jinja)
├── static/css/         # style.css
├── static/js/          # validation, lobby, solo, partie, dessin, contrôles, fin, arène
└── docs/               # présentation, schéma BDD, architecture, bonus, améliorations
```

Détails : [docs/architecture.md](docs/architecture.md) ·
[docs/schema.md](docs/schema.md) ·
[docs/presentation.md](docs/presentation.md) ·
[docs/bonus.md](docs/bonus.md) ·
[docs/ameliorations.md](docs/ameliorations.md)

## Sécurité (résumé)

- Requêtes SQL **paramétrées** (`?`) : pas d’injection SQL. Le tri du
  classement est choisi dans une liste blanche, jamais collé depuis l’URL.
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
