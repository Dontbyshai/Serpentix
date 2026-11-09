# -*- coding: utf-8 -*-
"""
database.py — Accès à la base SQLite de Serpentix
-------------------------------------------------
Centralise toutes les requêtes SQL pour :
  - initialiser les tables (+ migration légère)
  - CRUD utilisateurs
  - coins / skins
  - parties et scores / classement

Les commentaires sont volontairement détaillés (projet NSI).
"""

import os
import sqlite3
from contextlib import contextmanager

# Chemin absolu du fichier SQLite (à côté de ce module)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "serpentix.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

# Catalogue des skins (couleurs du serpent uniquement — l'UI reste noir & blanc)
# id → hex, prix en coins, libellé FR
SKINS = {
    "blanc": {"hex": "#ffffff", "prix": 0, "nom": "Blanc"},
    "rouge": {"hex": "#ef4444", "prix": 40, "nom": "Rouge"},
    "vert": {"hex": "#22c55e", "prix": 40, "nom": "Vert"},
    "orange": {"hex": "#f97316", "prix": 60, "nom": "Orange"},
    "jaune": {"hex": "#eab308", "prix": 60, "nom": "Jaune"},
}

SKIN_PAR_HEX = {v["hex"].lower(): k for k, v in SKINS.items()}


def get_connection():
    """Ouvre une connexion SQLite avec clés étrangères activées."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_cursor():
    """
    Gestionnaire de contexte : ouvre, commit / rollback, ferme.
    Usage :
        with db_cursor() as cur:
            cur.execute(...)
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _colonnes_utilisateurs():
    """Liste les noms de colonnes de la table utilisateurs."""
    with db_cursor() as cur:
        cur.execute("PRAGMA table_info(utilisateurs)")
        return {row["name"] for row in cur.fetchall()}


def migrer_si_besoin():
    """Ajoute coins / skins_debloques si une vieille BDD existe encore."""
    cols = _colonnes_utilisateurs()
    if not cols:
        return
    with db_cursor() as cur:
        if "coins" not in cols:
            cur.execute(
                "ALTER TABLE utilisateurs ADD COLUMN coins INTEGER NOT NULL DEFAULT 0"
            )
        if "skins_debloques" not in cols:
            cur.execute(
                "ALTER TABLE utilisateurs ADD COLUMN skins_debloques "
                "TEXT NOT NULL DEFAULT 'blanc'"
            )


def init_db():
    """Crée les tables si elles n'existent pas encore (premier lancement)."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()
    conn = get_connection()
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()
    migrer_si_besoin()


# ---------------------------------------------------------------------------
# UTILISATEURS — CRUD
# ---------------------------------------------------------------------------

def creer_utilisateur(pseudo, email, mot_de_passe_hash, couleur_skin="#ffffff",
                      est_admin=0, coins=0, skins_debloques="blanc"):
    """Insère un nouvel utilisateur. Retourne son id."""
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO utilisateurs
                (pseudo, email, mot_de_passe_hash, couleur_skin, est_admin,
                 coins, skins_debloques)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (pseudo, email, mot_de_passe_hash, couleur_skin, est_admin,
             coins, skins_debloques),
        )
        return cur.lastrowid


def _row_vers_user(row):
    """Convertit une Row en dict + liste de skins débloqués."""
    if not row:
        return None
    d = dict(row)
    raw = d.get("skins_debloques") or "blanc"
    d["skins_liste"] = [s.strip() for s in raw.split(",") if s.strip()]
    if "blanc" not in d["skins_liste"]:
        d["skins_liste"].insert(0, "blanc")
    d["coins"] = int(d.get("coins") or 0)
    return d


def lister_utilisateurs():
    """Retourne la liste de tous les utilisateurs (sans le hash)."""
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, pseudo, email, couleur_skin, est_admin, date_inscription,
                   coins, skins_debloques
            FROM utilisateurs
            ORDER BY date_inscription DESC
            """
        )
        return [_row_vers_user(row) for row in cur.fetchall()]


def obtenir_utilisateur(user_id):
    """Retourne un utilisateur par son id, ou None."""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM utilisateurs WHERE id = ?", (user_id,))
        return _row_vers_user(cur.fetchone())


def obtenir_par_pseudo(pseudo):
    """Retourne un utilisateur par son pseudo (pour la connexion)."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM utilisateurs WHERE LOWER(pseudo) = LOWER(?)",
            (pseudo,),
        )
        return _row_vers_user(cur.fetchone())


def obtenir_par_email(email):
    """Retourne un utilisateur par e-mail (contrôle d'unicité)."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM utilisateurs WHERE LOWER(email) = LOWER(?)",
            (email,),
        )
        return _row_vers_user(cur.fetchone())


def mettre_a_jour_utilisateur(user_id, pseudo=None, email=None, couleur_skin=None,
                               mot_de_passe_hash=None, est_admin=None,
                               coins=None, skins_debloques=None):
    """
    Met à jour les champs fournis (les autres restent inchangés).
    Retourne True si une ligne a été modifiée.
    """
    user = obtenir_utilisateur(user_id)
    if not user:
        return False

    nouveau_pseudo = pseudo if pseudo is not None else user["pseudo"]
    nouvel_email = email if email is not None else user["email"]
    nouvelle_couleur = couleur_skin if couleur_skin is not None else user["couleur_skin"]
    nouveau_hash = mot_de_passe_hash if mot_de_passe_hash is not None else user["mot_de_passe_hash"]
    nouvel_admin = est_admin if est_admin is not None else user["est_admin"]
    nouveaux_coins = coins if coins is not None else user["coins"]
    nouveaux_skins = skins_debloques if skins_debloques is not None else ",".join(user["skins_liste"])

    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE utilisateurs
            SET pseudo = ?, email = ?, couleur_skin = ?, mot_de_passe_hash = ?,
                est_admin = ?, coins = ?, skins_debloques = ?
            WHERE id = ?
            """,
            (nouveau_pseudo, nouvel_email, nouvelle_couleur, nouveau_hash,
             nouvel_admin, nouveaux_coins, nouveaux_skins, user_id),
        )
        return cur.rowcount > 0


def supprimer_utilisateur(user_id):
    """Supprime un utilisateur. Retourne True si suppression effectuée."""
    with db_cursor() as cur:
        cur.execute("DELETE FROM utilisateurs WHERE id = ?", (user_id,))
        return cur.rowcount > 0


def ajouter_coins(user_id, montant):
    """Ajoute des coins (montant >= 0). Retourne le nouveau solde."""
    if montant < 0:
        raise ValueError("montant négatif interdit")
    user = obtenir_utilisateur(user_id)
    if not user:
        return None
    nouveau = user["coins"] + int(montant)
    mettre_a_jour_utilisateur(user_id, coins=nouveau)
    return nouveau


def acheter_skin(user_id, skin_id):
    """
    Débloque un skin si le joueur a assez de coins.
    Retourne (ok: bool, message: str, user: dict|None).
    """
    if skin_id not in SKINS:
        return False, "Skin inconnu.", None
    user = obtenir_utilisateur(user_id)
    if not user:
        return False, "Joueur introuvable.", None
    if skin_id in user["skins_liste"]:
        return False, "Tu possèdes déjà ce skin.", user
    prix = SKINS[skin_id]["prix"]
    if user["coins"] < prix:
        return False, f"Pas assez de coins (il faut {prix}).", user
    skins = user["skins_liste"] + [skin_id]
    mettre_a_jour_utilisateur(
        user_id,
        coins=user["coins"] - prix,
        skins_debloques=",".join(skins),
    )
    return True, f"Skin « {SKINS[skin_id]['nom']} » débloqué !", obtenir_utilisateur(user_id)


def equiper_skin(user_id, skin_id):
    """Équipe un skin déjà débloqué. Retourne (ok, message, user)."""
    if skin_id not in SKINS:
        return False, "Skin inconnu.", None
    user = obtenir_utilisateur(user_id)
    if not user:
        return False, "Joueur introuvable.", None
    if skin_id not in user["skins_liste"]:
        return False, "Ce skin n'est pas débloqué.", user
    mettre_a_jour_utilisateur(user_id, couleur_skin=SKINS[skin_id]["hex"])
    return True, f"Skin « {SKINS[skin_id]['nom']} » équipé.", obtenir_utilisateur(user_id)


def skin_id_depuis_hex(hex_couleur):
    """Retrouve l'id de skin à partir d'un hex, défaut blanc."""
    return SKIN_PAR_HEX.get((hex_couleur or "").lower(), "blanc")


# ---------------------------------------------------------------------------
# PARTIES & SCORES
# ---------------------------------------------------------------------------

def creer_partie(code, createur_id):
    """Crée une partie en attente et enregistre la participation du créateur."""
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO parties (code, statut, createur_id) VALUES (?, 'attente', ?)",
            (code, createur_id),
        )
        partie_id = cur.lastrowid
        cur.execute(
            "INSERT INTO participations (utilisateur_id, partie_id) VALUES (?, ?)",
            (createur_id, partie_id),
        )
        return partie_id


def obtenir_partie_par_code(code):
    """Retrouve une partie via son code (insensible à la casse)."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM parties WHERE UPPER(code) = UPPER(?)",
            (code,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def ajouter_participant(partie_id, utilisateur_id):
    """Ajoute un 2e joueur à une partie (ignore si déjà présent)."""
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT OR IGNORE INTO participations (utilisateur_id, partie_id)
            VALUES (?, ?)
            """,
            (utilisateur_id, partie_id),
        )


def demarrer_partie(partie_id):
    """Passe le statut de la partie à 'en_cours'."""
    with db_cursor() as cur:
        cur.execute(
            "UPDATE parties SET statut = 'en_cours' WHERE id = ?",
            (partie_id,),
        )


def terminer_partie(partie_id, vainqueur_id, scores):
    """
    Clôture une partie et verse les coins (score + bonus victoire).
    scores : dict {utilisateur_id: score}
    """
    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE parties
            SET statut = 'terminee', vainqueur_id = ?, date_fin = datetime('now', 'localtime')
            WHERE id = ?
            """,
            (vainqueur_id, partie_id),
        )
        for uid, score in scores.items():
            a_gagne = 1 if uid == vainqueur_id else 0
            cur.execute(
                """
                UPDATE participations
                SET score = ?, a_gagne = ?
                WHERE partie_id = ? AND utilisateur_id = ?
                """,
                (score, a_gagne, partie_id, uid),
            )
    # Coins hors du curseur (ajouter_coins ouvre sa propre transaction)
    for uid, score in scores.items():
        gain = int(score) + (15 if uid == vainqueur_id else 0)
        if gain > 0:
            ajouter_coins(uid, gain)


def classement(limit=20):
    """
    Classement global : victoires, parties jouées, score total, coins.
    """
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT
                u.id,
                u.pseudo,
                u.couleur_skin,
                u.coins,
                COUNT(p.id) AS parties_jouees,
                COALESCE(SUM(p.a_gagne), 0) AS victoires,
                COALESCE(SUM(p.score), 0) AS score_total
            FROM utilisateurs u
            LEFT JOIN participations p ON p.utilisateur_id = u.id
            GROUP BY u.id
            ORDER BY victoires DESC, score_total DESC, u.coins DESC, u.pseudo ASC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


def historique_utilisateur(user_id, limit=10):
    """Dernières parties d'un joueur."""
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT
                pa.code,
                pa.statut,
                pa.date_creation,
                pa.date_fin,
                p.score,
                p.a_gagne,
                pa.vainqueur_id
            FROM participations p
            JOIN parties pa ON pa.id = p.partie_id
            WHERE p.utilisateur_id = ?
            ORDER BY pa.date_creation DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        return [dict(row) for row in cur.fetchall()]
