# Serpentix

Projet NSI — **site web dynamique avec base de données** + jeu navigateur
(mélange de *Snake* et *Slither.io*).

**Esthétique jeu** : interface **noir & blanc**, gros bouton **Jouer**.
Les seules couleurs sont les **skins** du serpent (rouge, vert, orange, jaune),
débloqués avec des **coins** gagnés en jouant.

## Fonctionnalités

- Landing page présentation + CTA **Jouer**
- Inscription / connexion (session Flask, mots de passe hachés)
- **Solo** (coins) ou **1v1** via code de salle partageable (Socket.IO)
- Boutique de skins (blanc gratuit ; couleurs payantes en coins)
- **CRUD utilisateurs** (exigence NSI) — accessible via le pied de page, hors menu jeu
- Validation formulaires **client (JS)** et **serveur (Python)**
- Classement (victoires / scores / coins en SQLite)
- Bonus turbo / bouclier

## Stack

| Couche | Techno |
|--------|--------|
| Serveur | Python 3, Flask, Flask-SocketIO |
| Base de données | SQLite (`schema.sql`) |
| Front | HTML, CSS, JavaScript (canvas) |

## Installation & lancement

```bash
git clone https://github.com/Dontbyshai/Serpentix.git
cd Serpentix

python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt

python app.py
```

Ouvre [http://127.0.0.1:5000](http://127.0.0.1:5000).

La base `serpentix.db` est créée automatiquement au premier lancement.

### Comptes de démonstration

Au premier démarrage (base vide), deux **joueurs** (pas d’admin) :

| Pseudo    | Mot de passe | Coins de départ |
|-----------|--------------|-----------------|
| `joueur1` | `joueur123`  | 100             |
| `joueur2` | `joueur2123` | 100             |

### Tester le 1v1

1. Onglet A : `joueur1` → **Jouer** → Générer un code → partager / entrer
2. Onglet B (navigation privée) : `joueur2` → Rejoindre avec le code
3. La partie démarre dès que les 2 joueurs sont dans la salle

### Coins & skins

| Skin   | Prix |
|--------|------|
| Blanc  | Gratuit (défaut) |
| Rouge  | 40 coins |
| Vert   | 40 coins |
| Orange | 60 coins |
| Jaune  | 60 coins |

- **Solo** : 1 pomme ≈ 1 coin (plafond 80 / partie)
- **1v1** : coins = score (pommes) + **15** si victoire

## Structure

```
serpentix/
├── app.py                 # Flask + routes + SocketIO
├── database.py            # SQLite (CRUD, coins, skins)
├── game_engine.py         # Moteur 1v1
├── schema.sql
├── docs/                  # Présentation NSI + schéma
├── templates/
└── static/css|js/
```

## Auteur

Projet réalisé par **Shaï** (NSI).

## Licence

Projet scolaire — usage libre pour démonstration éducative.
