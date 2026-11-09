# -*- coding: utf-8 -*-
"""
database.py — Accès à la base SQLite de Serpentix
=================================================

TOUTES les requêtes SQL du projet sont rassemblées ici. app.py n'écrit jamais
de SQL lui-même : il appelle les fonctions de ce module. Avantages :
  - un seul endroit à relire pour comprendre la base ;
  - on peut changer de SGBD (PostgreSQL…) sans toucher aux routes.

Sécurité : chaque requête utilise des PARAMÈTRES LIÉS (« ? »). Les valeurs
tapées par l'utilisateur ne sont jamais collées dans la chaîne SQL, donc une
injection SQL du type  ' OR 1=1 --  est impossible.

Tables (voir schema.sql et docs/schema.md) :
  utilisateurs, parties, participations.
"""

import os
import sqlite3
from contextlib import contextmanager

# Chemins absolus : le fichier .db est créé à côté de ce module, quel que soit
# le dossier depuis lequel on lance « python app.py ».
DOSSIER = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DOSSIER, "serpentix.db")
SCHEMA_PATH = os.path.join(DOSSIER, "schema.sql")

# Catalogue des skins : seules couleurs autorisées du site (l'UI reste noir & blanc).
# Clé = identifiant stocké en BDD ; hex = couleur dessinée ; prix en coins.
SKINS = {
    "blanc": {"hex": "#ffffff", "prix": 0, "nom": "Blanc"},
    "rouge": {"hex": "#ef4444", "prix": 40, "nom": "Rouge"},
    "vert": {"hex": "#22c55e", "prix": 40, "nom": "Vert"},
    "orange": {"hex": "#f97316", "prix": 60, "nom": "Orange"},
    "jaune": {"hex": "#eab308", "prix": 60, "nom": "Jaune"},
}

# Dictionnaire inverse « hex → id » (pour savoir quel skin est équipé)
SKIN_PAR_HEX = {v["hex"].lower(): k for k, v in SKINS.items()}

# Bonus de coins accordé au vainqueur d'un 1v1 (en plus de son score)
BONUS_VICTOIRE = 15


def get_connection():
    """
    Ouvre une connexion à la base.

    Retour : sqlite3.Connection.
    row_factory = sqlite3.Row permet d'écrire row["pseudo"] au lieu de row[1].
    PRAGMA foreign_keys = ON : SQLite n'applique les clés étrangères que si on
    le demande à chaque connexion.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_cursor():
    """
    Gestionnaire de contexte (« with ») : ouvre une connexion, donne un
    curseur, valide (commit) si tout va bien, annule (rollback) en cas
    d'erreur, et ferme TOUJOURS la connexion.

    Usage :
        with db_cursor() as cur:
            cur.execute("SELECT ...", (valeur,))
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()  # la base reste dans l'état d'avant (transaction)
        raise
    finally:
        conn.close()


def _colonnes_utilisateurs():
    """Retour : set des noms de colonnes de la table utilisateurs."""
    with db_cursor() as cur:
        cur.execute("PRAGMA table_info(utilisateurs)")
        return {row["name"] for row in cur.fetchall()}


def migrer_si_besoin():
    """
    Mise à jour d'une ANCIENNE base (créée avant l'ajout des coins/skins) :
    ajoute les colonnes manquantes sans perdre les données existantes.
    """
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
    """
    Crée les tables au premier lancement en exécutant schema.sql.
    « CREATE TABLE IF NOT EXISTS » rend l'opération sans danger si la base
    existe déjà : rien n'est effacé.
    """
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
# UTILISATEURS — CRUD (Create, Read, Update, Delete)
# ---------------------------------------------------------------------------

def creer_utilisateur(pseudo, email, mot_de_passe_hash, couleur_skin="#ffffff",
                      est_admin=0, coins=0, skins_debloques="blanc"):
    """
    CREATE — insère un utilisateur.

    Paramètres : pseudo, email, mot_de_passe_hash (jamais le mot de passe en
                 clair !), couleur_skin, est_admin, coins, skins_debloques.
    Retour     : int — id de la nouvelle ligne (cur.lastrowid).
    Lève sqlite3.IntegrityError si le pseudo ou l'e-mail existe déjà
    (contrainte UNIQUE) : app.py intercepte cette erreur.
    """
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
    """
    Convertit une ligne SQLite en dictionnaire Python enrichi.

    Paramètre : row (sqlite3.Row ou None).
    Retour    : dict (ou None) avec en plus la clé « skins_liste », la liste
                Python des skins débloqués (la BDD stocke "blanc,rouge").
    """
    if not row:
        return None
    d = dict(row)
    brut = d.get("skins_debloques") or "blanc"
    d["skins_liste"] = [s.strip() for s in brut.split(",") if s.strip()]
    if "blanc" not in d["skins_liste"]:
        d["skins_liste"].insert(0, "blanc")  # le skin blanc est toujours offert
    d["coins"] = int(d.get("coins") or 0)
    return d


def lister_utilisateurs():
    """
    READ collectif — tous les utilisateurs, du plus récent au plus ancien.
    Retour : liste de dict. On ne sélectionne PAS le hash du mot de passe.
    """
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, pseudo, email, couleur_skin, est_admin, date_inscription,
                   coins, skins_debloques
            FROM utilisateurs
            ORDER BY date_inscription DESC, id DESC
            """
        )
        return [_row_vers_user(row) for row in cur.fetchall()]


def obtenir_utilisateur(user_id):
    """READ individuel — Paramètre : user_id (int). Retour : dict ou None."""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM utilisateurs WHERE id = ?", (user_id,))
        return _row_vers_user(cur.fetchone())


def obtenir_par_pseudo(pseudo):
    """
    Cherche un utilisateur par pseudo, SANS tenir compte des majuscules
    (« Joueur1 » et « joueur1 » sont le même compte). Retour : dict ou None.
    """
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM utilisateurs WHERE LOWER(pseudo) = LOWER(?)",
            (pseudo,),
        )
        return _row_vers_user(cur.fetchone())


def obtenir_par_email(email):
    """Cherche un utilisateur par e-mail (contrôle d'unicité). Retour : dict ou None."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM utilisateurs WHERE LOWER(email) = LOWER(?)",
            (email,),
        )
        return _row_vers_user(cur.fetchone())


def mettre_a_jour_utilisateur(user_id, pseudo=None, email=None, couleur_skin=None,
                              mot_de_passe_hash=None, est_admin=None,
                              skins_debloques=None):
    """
    UPDATE — modifie les champs fournis ; ceux laissés à None ne changent pas.

    Paramètres : user_id + champs optionnels.
    Retour     : bool — True si une ligne a été modifiée.
    Les coins ne passent PAS par ici : ils ont leurs propres fonctions
    atomiques (ajouter_coins, acheter_skin) pour éviter les erreurs de calcul
    quand deux mises à jour arrivent en même temps.
    """
    user = obtenir_utilisateur(user_id)
    if not user:
        return False

    # Pour chaque champ : la nouvelle valeur si elle est fournie, sinon l'ancienne
    nouveau_pseudo = pseudo if pseudo is not None else user["pseudo"]
    nouvel_email = email if email is not None else user["email"]
    nouvelle_couleur = couleur_skin if couleur_skin is not None else user["couleur_skin"]
    nouveau_hash = (mot_de_passe_hash if mot_de_passe_hash is not None
                    else user["mot_de_passe_hash"])
    nouvel_admin = est_admin if est_admin is not None else user["est_admin"]
    nouveaux_skins = (skins_debloques if skins_debloques is not None
                      else ",".join(user["skins_liste"]))

    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE utilisateurs
            SET pseudo = ?, email = ?, couleur_skin = ?, mot_de_passe_hash = ?,
                est_admin = ?, skins_debloques = ?
            WHERE id = ?
            """,
            (nouveau_pseudo, nouvel_email, nouvelle_couleur, nouveau_hash,
             nouvel_admin, nouveaux_skins, user_id),
        )
        return cur.rowcount > 0


def supprimer_utilisateur(user_id):
    """
    DELETE — supprime un utilisateur.

    Paramètre : user_id. Retour : bool — True si une ligne a été supprimée.
    Problème rencontré : la table parties référence utilisateurs (createur_id,
    vainqueur_id). Avec les clés étrangères activées, SQLite REFUSAIT la
    suppression d'un joueur ayant déjà créé une partie (erreur 500).
    Solution, dans UNE transaction :
      1) on efface le lien « vainqueur » (vainqueur_id = NULL) ;
      2) on supprime les parties qu'il a créées (leurs participations
         partent avec, grâce à ON DELETE CASCADE) ;
      3) on supprime enfin l'utilisateur (ses participations partent aussi).
    """
    with db_cursor() as cur:
        cur.execute("UPDATE parties SET vainqueur_id = NULL WHERE vainqueur_id = ?",
                    (user_id,))
        cur.execute("DELETE FROM parties WHERE createur_id = ?", (user_id,))
        cur.execute("DELETE FROM utilisateurs WHERE id = ?", (user_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# COINS & SKINS
# ---------------------------------------------------------------------------

def ajouter_coins(user_id, montant):
    """
    Crédite des coins.

    Paramètres : user_id, montant (int >= 0).
    Retour     : int — nouveau solde (ou None si l'utilisateur n'existe pas).
    « coins = coins + ? » est calculé PAR SQLite en une seule requête : si
    deux gains arrivent en même temps, aucun n'est perdu (contrairement à
    « lire le solde en Python, ajouter, réécrire »).
    """
    montant = int(montant)
    if montant < 0:
        raise ValueError("montant négatif interdit")
    with db_cursor() as cur:
        cur.execute("UPDATE utilisateurs SET coins = coins + ? WHERE id = ?",
                    (montant, user_id))
        cur.execute("SELECT coins FROM utilisateurs WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return row["coins"] if row else None


def acheter_skin(user_id, skin_id):
    """
    Achète (débloque) un skin.

    Paramètres : user_id, skin_id (clé de SKINS).
    Retour     : (ok: bool, message: str, user: dict|None).
    Le débit utilise « WHERE coins >= prix » : si le solde est insuffisant,
    la requête ne modifie aucune ligne → impossible de passer en négatif,
    même en cliquant très vite plusieurs fois.
    """
    if skin_id not in SKINS:
        return False, "Skin inconnu.", None
    user = obtenir_utilisateur(user_id)
    if not user:
        return False, "Joueur introuvable.", None
    if skin_id in user["skins_liste"]:
        return False, "Tu possèdes déjà ce skin.", user
    prix = SKINS[skin_id]["prix"]
    nouveaux_skins = ",".join(user["skins_liste"] + [skin_id])
    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE utilisateurs
            SET coins = coins - ?, skins_debloques = ?
            WHERE id = ? AND coins >= ?
            """,
            (prix, nouveaux_skins, user_id, prix),
        )
        reussi = cur.rowcount == 1
    if not reussi:
        return False, f"Pas assez de coins (il faut {prix}).", user
    return True, f"Skin « {SKINS[skin_id]['nom']} » débloqué !", obtenir_utilisateur(user_id)


def equiper_skin(user_id, skin_id):
    """
    Équipe un skin déjà débloqué.
    Retour : (ok: bool, message: str, user: dict|None).
    """
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
    """Retour : id du skin correspondant à une couleur hex (« blanc » par défaut)."""
    return SKIN_PAR_HEX.get((hex_couleur or "").lower(), "blanc")


# ---------------------------------------------------------------------------
# PARTIES & SCORES
# ---------------------------------------------------------------------------

def creer_partie(code, createur_id):
    """
    Crée une partie « en attente » ET la participation de son créateur.
    Les deux INSERT sont dans la même transaction (tout ou rien).
    Retour : int — id de la partie.
    """
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
    """Retour : dict de la partie ayant ce code, ou None."""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM parties WHERE UPPER(code) = UPPER(?)", (code,))
        row = cur.fetchone()
        return dict(row) if row else None


def ajouter_participant(partie_id, utilisateur_id):
    """
    Inscrit un joueur dans une partie.
    INSERT OR IGNORE + contrainte UNIQUE (utilisateur_id, partie_id) :
    si la ligne existe déjà, SQLite l'ignore au lieu de planter.
    """
    with db_cursor() as cur:
        cur.execute(
            "INSERT OR IGNORE INTO participations (utilisateur_id, partie_id) VALUES (?, ?)",
            (utilisateur_id, partie_id),
        )


def demarrer_partie(partie_id):
    """Passe la partie au statut « en_cours »."""
    with db_cursor() as cur:
        cur.execute("UPDATE parties SET statut = 'en_cours' WHERE id = ?", (partie_id,))


def terminer_partie(partie_id, vainqueur_id, scores):
    """
    Clôture une partie : statut, vainqueur, scores, puis versement des coins.

    Paramètres :
      partie_id (int), vainqueur_id (int ou None si match nul),
      scores (dict {utilisateur_id: score}).
    Gain de chaque joueur = son score (+ BONUS_VICTOIRE s'il a gagné).
    La condition « statut != 'terminee' » empêche de payer deux fois la
    même partie si la fonction était appelée deux fois.
    """
    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE parties
            SET statut = 'terminee', vainqueur_id = ?,
                date_fin = datetime('now', 'localtime')
            WHERE id = ? AND statut != 'terminee'
            """,
            (vainqueur_id, partie_id),
        )
        if cur.rowcount == 0:
            return  # déjà clôturée : on ne recrédite pas
        for uid, score in scores.items():
            cur.execute(
                """
                UPDATE participations SET score = ?, a_gagne = ?
                WHERE partie_id = ? AND utilisateur_id = ?
                """,
                (score, 1 if uid == vainqueur_id else 0, partie_id, uid),
            )
    for uid, score in scores.items():
        gain = int(score) + (BONUS_VICTOIRE if uid == vainqueur_id else 0)
        if gain > 0:
            ajouter_coins(uid, gain)


def classement(limit=20):
    """
    Classement global, calculé par SQL (jointure + agrégats).

    Retour : liste de dict (pseudo, victoires, score_total, parties_jouees, coins).
    LEFT JOIN : un joueur sans partie apparaît quand même (avec 0).
    On ne compte que les parties TERMINÉES (pas les salles abandonnées).
    """
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT
                u.id, u.pseudo, u.couleur_skin, u.coins,
                COUNT(pa.id)                  AS parties_jouees,
                COALESCE(SUM(p.a_gagne), 0)   AS victoires,
                COALESCE(SUM(p.score), 0)     AS score_total
            FROM utilisateurs u
            LEFT JOIN participations p ON p.utilisateur_id = u.id
            LEFT JOIN parties pa ON pa.id = p.partie_id AND pa.statut = 'terminee'
            GROUP BY u.id
            ORDER BY victoires DESC, score_total DESC, u.coins DESC, u.pseudo ASC
            LIMIT ?
            """,
            (limit,),
        )
        rows = [dict(row) for row in cur.fetchall()]
    return rows


def historique_utilisateur(user_id, limit=10):
    """
    Dernières parties d'un joueur (pour le profil et la fiche joueur).
    Retour : liste de dict (code, statut, dates, score, a_gagne, vainqueur_id).
    """
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT pa.code, pa.statut, pa.date_creation, pa.date_fin,
                   p.score, p.a_gagne, pa.vainqueur_id
            FROM participations p
            JOIN parties pa ON pa.id = p.partie_id
            WHERE p.utilisateur_id = ?
            ORDER BY pa.date_creation DESC, pa.id DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        return [dict(row) for row in cur.fetchall()]
