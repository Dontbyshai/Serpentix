# -*- coding: utf-8 -*-
"""
app.py — Serveur web Serpentix (Flask + SocketIO)
=================================================
Projet NSI : site dynamique avec base SQL + jeu 1v1 temps réel.

Lancement :
    python app.py
Puis ouvrir http://127.0.0.1:5000

Fonctionnalités :
  - Inscription / connexion (session + mots de passe hachés)
  - CRUD utilisateurs (formulaires + validation client ET serveur)
  - Lobby créer / rejoindre une partie
  - Jeu canvas 1v1 (Snake + Slither) via WebSocket
  - Classement et profil (couleur de skin)
"""

import os
import re
import threading
import time

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash

import database as db
from game_engine import PartieEnCours, generer_code

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)

# Clé de session Flask — à changer en production (variable d'environnement)
# Ne jamais committer un vrai secret de production.
app.config["SECRET_KEY"] = os.environ.get(
    "SERPENTIX_SECRET_KEY",
    "serpentix-nsi-dev-key-a-changer",
)

# SocketIO : async_mode threading (simple, pas besoin d'eventlet forcé)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Parties en mémoire : code → PartieEnCours
PARTIES = {}
PARTIES_LOCK = threading.Lock()

# Boucle de jeu déjà démarrée ?
_boucle_demarree = False
TICK_INTERVAL = 0.10  # 10 images / seconde


# ---------------------------------------------------------------------------
# Helpers validation (côté serveur)
# ---------------------------------------------------------------------------

def valider_pseudo(pseudo):
    """Pseudo : 3 à 20 caractères, lettres/chiffres/_/- uniquement."""
    if not pseudo or not isinstance(pseudo, str):
        return "Le pseudo est obligatoire."
    pseudo = pseudo.strip()
    if len(pseudo) < 3 or len(pseudo) > 20:
        return "Le pseudo doit faire entre 3 et 20 caractères."
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", pseudo):
        return "Le pseudo ne peut contenir que lettres, chiffres, _ et -."
    return None


def valider_email(email):
    """E-mail simple (présence de @ et d'un point après)."""
    if not email or not isinstance(email, str):
        return "L'e-mail est obligatoire."
    email = email.strip()
    if len(email) > 100:
        return "E-mail trop long."
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return "Format d'e-mail invalide."
    return None


def valider_mot_de_passe(mdp, obligatoire=True):
    """Mot de passe : au moins 6 caractères."""
    if not mdp:
        return "Le mot de passe est obligatoire." if obligatoire else None
    if len(mdp) < 6:
        return "Le mot de passe doit contenir au moins 6 caractères."
    if len(mdp) > 100:
        return "Mot de passe trop long."
    return None


def valider_couleur(couleur):
    """Couleur hexadécimale #RRGGBB."""
    if not couleur or not re.fullmatch(r"#[0-9A-Fa-f]{6}", couleur):
        return "Couleur invalide (format #RRGGBB attendu)."
    return None


def utilisateur_connecte():
    """Retourne l'utilisateur de la session, ou None."""
    uid = session.get("user_id")
    if not uid:
        return None
    return db.obtenir_utilisateur(uid)


def login_requis(f):
    """Décorateur : redirige vers /connexion si non connecté."""
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if not utilisateur_connecte():
            flash("Connecte-toi pour accéder à cette page.", "warning")
            return redirect(url_for("connexion", next=request.path))
        return f(*args, **kwargs)

    return decorated


def admin_requis(f):
    """Décorateur : réservé aux administrateurs."""
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        user = utilisateur_connecte()
        if not user:
            flash("Connecte-toi pour accéder à cette page.", "warning")
            return redirect(url_for("connexion"))
        if not user.get("est_admin"):
            flash("Accès réservé aux administrateurs.", "danger")
            return redirect(url_for("accueil"))
        return f(*args, **kwargs)

    return decorated


# ---------------------------------------------------------------------------
# Boucle de jeu (ticks serveur)
# ---------------------------------------------------------------------------

def boucle_jeu():
    """Thread daemon : avance toutes les parties en cours et diffuse l'état."""
    while True:
        time.sleep(TICK_INTERVAL)
        with PARTIES_LOCK:
            codes = list(PARTIES.keys())
        for code in codes:
            with PARTIES_LOCK:
                partie = PARTIES.get(code)
                if not partie or partie.statut != "en_cours":
                    continue
                finie = partie.tick()
                etat = partie.etat_public()
                a_sauver = None
                if finie:
                    a_sauver = (
                        partie.partie_db_id,
                        etat.get("vainqueur_id"),
                        partie.scores_par_id(),
                    )
            # Diffusion hors du lock
            socketio.emit("etat_jeu", etat, room=code)
            if a_sauver:
                pid, vainqueur, scores = a_sauver
                if pid:
                    try:
                        db.terminer_partie(pid, vainqueur, scores)
                    except Exception as exc:
                        app.logger.error("Erreur sauvegarde partie: %s", exc)


def assurer_boucle():
    """Démarre la boucle une seule fois."""
    global _boucle_demarree
    if not _boucle_demarree:
        t = threading.Thread(target=boucle_jeu, daemon=True)
        t.start()
        _boucle_demarree = True


# ---------------------------------------------------------------------------
# Routes HTML
# ---------------------------------------------------------------------------

@app.context_processor
def inject_user():
    """Rend `current_user` disponible dans tous les templates."""
    return {"current_user": utilisateur_connecte()}


@app.route("/")
def accueil():
    """Page d'accueil : présentation du jeu."""
    return render_template("accueil.html")


@app.route("/inscription", methods=["GET", "POST"])
def inscription():
    """Création d'un compte (CREATE utilisateur)."""
    if utilisateur_connecte():
        return redirect(url_for("accueil"))

    erreurs = {}
    valeurs = {"pseudo": "", "email": "", "couleur_skin": "#22c55e"}

    if request.method == "POST":
        pseudo = (request.form.get("pseudo") or "").strip()
        email = (request.form.get("email") or "").strip()
        mdp = request.form.get("mot_de_passe") or ""
        mdp2 = request.form.get("mot_de_passe2") or ""
        couleur = request.form.get("couleur_skin") or "#22c55e"

        valeurs = {"pseudo": pseudo, "email": email, "couleur_skin": couleur}

        # --- Validation serveur ---
        e = valider_pseudo(pseudo)
        if e:
            erreurs["pseudo"] = e
        e = valider_email(email)
        if e:
            erreurs["email"] = e
        e = valider_mot_de_passe(mdp)
        if e:
            erreurs["mot_de_passe"] = e
        if mdp != mdp2:
            erreurs["mot_de_passe2"] = "Les mots de passe ne correspondent pas."
        e = valider_couleur(couleur)
        if e:
            erreurs["couleur_skin"] = e

        # Unicité
        if not erreurs.get("pseudo") and db.obtenir_par_pseudo(pseudo):
            erreurs["pseudo"] = "Ce pseudo est déjà pris."
        if not erreurs.get("email") and db.obtenir_par_email(email):
            erreurs["email"] = "Cet e-mail est déjà utilisé."

        if not erreurs:
            # Premier utilisateur = admin (pratique pour la démo NSI)
            deja = db.lister_utilisateurs()
            est_admin = 1 if len(deja) == 0 else 0
            hash_mdp = generate_password_hash(mdp)
            uid = db.creer_utilisateur(pseudo, email, hash_mdp, couleur, est_admin)
            session["user_id"] = uid
            flash(f"Bienvenue {pseudo} ! Compte créé.", "success")
            return redirect(url_for("accueil"))

    return render_template("inscription.html", erreurs=erreurs, valeurs=valeurs)


@app.route("/connexion", methods=["GET", "POST"])
def connexion():
    """Connexion (session)."""
    if utilisateur_connecte():
        return redirect(url_for("accueil"))

    erreur = None
    pseudo_val = ""

    if request.method == "POST":
        pseudo = (request.form.get("pseudo") or "").strip()
        mdp = request.form.get("mot_de_passe") or ""
        pseudo_val = pseudo

        user = db.obtenir_par_pseudo(pseudo)
        if not user or not check_password_hash(user["mot_de_passe_hash"], mdp):
            erreur = "Pseudo ou mot de passe incorrect."
        else:
            session["user_id"] = user["id"]
            flash(f"Bon retour, {user['pseudo']} !", "success")
            nxt = request.args.get("next") or url_for("accueil")
            return redirect(nxt)

    return render_template("connexion.html", erreur=erreur, pseudo=pseudo_val)


@app.route("/deconnexion")
def deconnexion():
    """Ferme la session."""
    session.clear()
    flash("Tu es déconnecté.", "info")
    return redirect(url_for("accueil"))


@app.route("/profil", methods=["GET", "POST"])
@login_requis
def profil():
    """Profil : changer couleur / e-mail / mot de passe."""
    user = utilisateur_connecte()
    erreurs = {}

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        couleur = request.form.get("couleur_skin") or user["couleur_skin"]
        mdp = request.form.get("mot_de_passe") or ""
        mdp2 = request.form.get("mot_de_passe2") or ""

        e = valider_email(email)
        if e:
            erreurs["email"] = e
        else:
            autre = db.obtenir_par_email(email)
            if autre and autre["id"] != user["id"]:
                erreurs["email"] = "Cet e-mail est déjà utilisé."

        e = valider_couleur(couleur)
        if e:
            erreurs["couleur_skin"] = e

        nouveau_hash = None
        if mdp or mdp2:
            e = valider_mot_de_passe(mdp)
            if e:
                erreurs["mot_de_passe"] = e
            elif mdp != mdp2:
                erreurs["mot_de_passe2"] = "Les mots de passe ne correspondent pas."
            else:
                nouveau_hash = generate_password_hash(mdp)

        if not erreurs:
            db.mettre_a_jour_utilisateur(
                user["id"],
                email=email,
                couleur_skin=couleur,
                mot_de_passe_hash=nouveau_hash,
            )
            flash("Profil mis à jour.", "success")
            return redirect(url_for("profil"))

        user = db.obtenir_utilisateur(user["id"])

    histo = db.historique_utilisateur(user["id"])
    return render_template("profil.html", user=user, erreurs=erreurs, historique=histo)


@app.route("/classement")
def classement():
    """Page classement (scores depuis la BDD)."""
    rows = db.classement()
    return render_template("classement.html", classement=rows)


@app.route("/jouer")
@login_requis
def jouer():
    """Lobby : créer ou rejoindre une salle."""
    return render_template("lobby.html")


@app.route("/partie/<code>")
@login_requis
def partie(code):
    """Page de jeu canvas pour une salle donnée."""
    return render_template("partie.html", code=code.upper())


@app.route("/solo")
@login_requis
def solo():
    """Mode solo (entraînement) — un serpent vs soi-même / pommes."""
    return render_template("solo.html")


# ---------------------------------------------------------------------------
# CRUD utilisateurs (admin) — exigence NSI
# ---------------------------------------------------------------------------

@app.route("/utilisateurs")
@login_requis
def liste_utilisateurs():
    """READ collectif : liste tous les utilisateurs."""
    users = db.lister_utilisateurs()
    return render_template("utilisateurs_liste.html", utilisateurs=users)


@app.route("/utilisateurs/<int:uid>")
@login_requis
def detail_utilisateur(uid):
    """READ individuel."""
    user = db.obtenir_utilisateur(uid)
    if not user:
        flash("Utilisateur introuvable.", "danger")
        return redirect(url_for("liste_utilisateurs"))
    histo = db.historique_utilisateur(uid)
    return render_template("utilisateur_detail.html", user=user, historique=histo)


@app.route("/utilisateurs/<int:uid>/modifier", methods=["GET", "POST"])
@login_requis
def modifier_utilisateur(uid):
    """UPDATE — formulaire de mise à jour."""
    courant = utilisateur_connecte()
    # Soi-même ou admin
    if courant["id"] != uid and not courant.get("est_admin"):
        flash("Tu ne peux modifier que ton propre profil ici (ou être admin).", "danger")
        return redirect(url_for("liste_utilisateurs"))

    user = db.obtenir_utilisateur(uid)
    if not user:
        flash("Utilisateur introuvable.", "danger")
        return redirect(url_for("liste_utilisateurs"))

    erreurs = {}
    if request.method == "POST":
        pseudo = (request.form.get("pseudo") or "").strip()
        email = (request.form.get("email") or "").strip()
        couleur = request.form.get("couleur_skin") or user["couleur_skin"]
        mdp = request.form.get("mot_de_passe") or ""

        e = valider_pseudo(pseudo)
        if e:
            erreurs["pseudo"] = e
        else:
            autre = db.obtenir_par_pseudo(pseudo)
            if autre and autre["id"] != uid:
                erreurs["pseudo"] = "Pseudo déjà pris."

        e = valider_email(email)
        if e:
            erreurs["email"] = e
        else:
            autre = db.obtenir_par_email(email)
            if autre and autre["id"] != uid:
                erreurs["email"] = "E-mail déjà utilisé."

        e = valider_couleur(couleur)
        if e:
            erreurs["couleur_skin"] = e

        nouveau_hash = None
        if mdp:
            e = valider_mot_de_passe(mdp)
            if e:
                erreurs["mot_de_passe"] = e
            else:
                nouveau_hash = generate_password_hash(mdp)

        est_admin = user["est_admin"]
        if courant.get("est_admin") and request.form.get("est_admin") is not None:
            est_admin = 1 if request.form.get("est_admin") == "1" else 0

        if not erreurs:
            db.mettre_a_jour_utilisateur(
                uid,
                pseudo=pseudo,
                email=email,
                couleur_skin=couleur,
                mot_de_passe_hash=nouveau_hash,
                est_admin=est_admin,
            )
            flash("Utilisateur mis à jour.", "success")
            return redirect(url_for("detail_utilisateur", uid=uid))

        user = {
            **user,
            "pseudo": pseudo,
            "email": email,
            "couleur_skin": couleur,
        }

    return render_template(
        "utilisateur_modifier.html",
        user=user,
        erreurs=erreurs,
        est_admin_courant=bool(courant.get("est_admin")),
    )


@app.route("/utilisateurs/<int:uid>/supprimer", methods=["POST"])
@login_requis
def supprimer_utilisateur(uid):
    """DELETE — bouton de suppression (admin ou soi-même)."""
    courant = utilisateur_connecte()
    if courant["id"] != uid and not courant.get("est_admin"):
        flash("Suppression non autorisée.", "danger")
        return redirect(url_for("liste_utilisateurs"))

    if courant["id"] == uid:
        db.supprimer_utilisateur(uid)
        session.clear()
        flash("Ton compte a été supprimé.", "info")
        return redirect(url_for("accueil"))

    db.supprimer_utilisateur(uid)
    flash("Utilisateur supprimé.", "success")
    return redirect(url_for("liste_utilisateurs"))


@app.route("/utilisateurs/nouveau", methods=["GET", "POST"])
@admin_requis
def nouvel_utilisateur():
    """CREATE via page admin (en plus de /inscription)."""
    erreurs = {}
    valeurs = {"pseudo": "", "email": "", "couleur_skin": "#3b82f6", "est_admin": "0"}

    if request.method == "POST":
        pseudo = (request.form.get("pseudo") or "").strip()
        email = (request.form.get("email") or "").strip()
        mdp = request.form.get("mot_de_passe") or ""
        couleur = request.form.get("couleur_skin") or "#3b82f6"
        est_admin = 1 if request.form.get("est_admin") == "1" else 0
        valeurs = {
            "pseudo": pseudo,
            "email": email,
            "couleur_skin": couleur,
            "est_admin": str(est_admin),
        }

        e = valider_pseudo(pseudo)
        if e:
            erreurs["pseudo"] = e
        elif db.obtenir_par_pseudo(pseudo):
            erreurs["pseudo"] = "Pseudo déjà pris."
        e = valider_email(email)
        if e:
            erreurs["email"] = e
        elif db.obtenir_par_email(email):
            erreurs["email"] = "E-mail déjà utilisé."
        e = valider_mot_de_passe(mdp)
        if e:
            erreurs["mot_de_passe"] = e
        e = valider_couleur(couleur)
        if e:
            erreurs["couleur_skin"] = e

        if not erreurs:
            db.creer_utilisateur(
                pseudo, email, generate_password_hash(mdp), couleur, est_admin
            )
            flash(f"Utilisateur {pseudo} créé.", "success")
            return redirect(url_for("liste_utilisateurs"))

    return render_template("utilisateur_nouveau.html", erreurs=erreurs, valeurs=valeurs)


# ---------------------------------------------------------------------------
# API lobby (JSON) — création / rejoindre
# ---------------------------------------------------------------------------

@app.route("/api/partie/creer", methods=["POST"])
@login_requis
def api_creer_partie():
    """Crée une salle + enregistrement BDD. Retourne le code."""
    user = utilisateur_connecte()
    # Code unique
    for _ in range(20):
        code = generer_code()
        if not db.obtenir_partie_par_code(code) and code not in PARTIES:
            break
    else:
        return jsonify({"ok": False, "erreur": "Impossible de générer un code."}), 500

    partie_id = db.creer_partie(code, user["id"])
    with PARTIES_LOCK:
        PARTIES[code] = PartieEnCours(code, partie_db_id=partie_id)
    assurer_boucle()
    return jsonify({"ok": True, "code": code})


@app.route("/api/partie/rejoindre", methods=["POST"])
@login_requis
def api_rejoindre_partie():
    """Vérifie qu'une salle existe et a de la place."""
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or request.form.get("code") or "").strip().upper()
    if not code:
        return jsonify({"ok": False, "erreur": "Code manquant."}), 400

    with PARTIES_LOCK:
        partie = PARTIES.get(code)
        if not partie:
            # Peut-être encore en BDD mais pas en mémoire → recrée
            row = db.obtenir_partie_par_code(code)
            if not row or row["statut"] != "attente":
                return jsonify({"ok": False, "erreur": "Partie introuvable ou déjà commencée."}), 404
            partie = PartieEnCours(code, partie_db_id=row["id"])
            PARTIES[code] = partie
        if len(partie.ordre_sids) >= 2 and partie.statut != "attente":
            return jsonify({"ok": False, "erreur": "Partie pleine."}), 400
        if len(partie.ordre_sids) >= 2:
            return jsonify({"ok": False, "erreur": "Partie pleine (2 joueurs max)."}), 400

    user = utilisateur_connecte()
    row = db.obtenir_partie_par_code(code)
    if row:
        db.ajouter_participant(row["id"], user["id"])
    assurer_boucle()
    return jsonify({"ok": True, "code": code})


# ---------------------------------------------------------------------------
# SocketIO — temps réel
# ---------------------------------------------------------------------------

@socketio.on("connect")
def on_connect():
    """Connexion WebSocket (pas encore dans une salle)."""
    pass


@socketio.on("rejoindre_salle")
def on_rejoindre_salle(data):
    """Le client rejoint la room SocketIO et s'ajoute à la partie."""
    user = utilisateur_connecte()
    if not user:
        emit("erreur", {"message": "Non authentifié."})
        return

    code = (data.get("code") or "").upper()
    with PARTIES_LOCK:
        partie = PARTIES.get(code)
        if not partie:
            emit("erreur", {"message": "Salle introuvable."})
            return
        ok = partie.ajouter_joueur(
            request.sid, user["id"], user["pseudo"], user["couleur_skin"]
        )
        if not ok:
            emit("erreur", {"message": "Salle pleine."})
            return
        join_room(code)
        etat = partie.etat_public()
        demarrer = partie.peut_demarrer()
        if demarrer:
            partie.demarrer()
            if partie.partie_db_id:
                db.demarrer_partie(partie.partie_db_id)
            etat = partie.etat_public()

    emit("etat_jeu", etat, room=code)
    if demarrer:
        emit("partie_lancee", {"code": code}, room=code)


@socketio.on("direction")
def on_direction(data):
    """Le joueur change de direction (flèches / WASD)."""
    code = (data.get("code") or "").upper()
    dx = int(data.get("dx", 0))
    dy = int(data.get("dy", 0))
    with PARTIES_LOCK:
        partie = PARTIES.get(code)
        if partie:
            partie.traiter_direction(request.sid, dx, dy)


@socketio.on("quitter_salle")
def on_quitter_salle(data):
    code = (data.get("code") or "").upper()
    with PARTIES_LOCK:
        partie = PARTIES.get(code)
        if partie:
            partie.retirer_joueur(request.sid)
            leave_room(code)
            etat = partie.etat_public()
            if len(partie.ordre_sids) == 0 and partie.statut != "en_cours":
                PARTIES.pop(code, None)
                etat = None
    if etat:
        emit("etat_jeu", etat, room=code)


@socketio.on("disconnect")
def on_disconnect():
    """Nettoyage si le navigateur se ferme."""
    sid = request.sid
    with PARTIES_LOCK:
        a_notifier = []
        a_supprimer = []
        for code, partie in list(PARTIES.items()):
            if sid in partie.joueurs:
                partie.retirer_joueur(sid)
                a_notifier.append((code, partie.etat_public()))
                if len(partie.ordre_sids) == 0:
                    a_supprimer.append(code)
        for code in a_supprimer:
            PARTIES.pop(code, None)
    for code, etat in a_notifier:
        emit("etat_jeu", etat, room=code)


# ---------------------------------------------------------------------------
# Démarrage
# ---------------------------------------------------------------------------

def creer_admin_demo_si_vide():
    """Si la BDD est vide, crée un compte démo (documenté dans le README)."""
    if not db.lister_utilisateurs():
        db.creer_utilisateur(
            "admin",
            "admin@serpentix.local",
            generate_password_hash("admin123"),
            "#eab308",
            est_admin=1,
        )
        db.creer_utilisateur(
            "joueur2",
            "joueur2@serpentix.local",
            generate_password_hash("joueur2123"),
            "#3b82f6",
            est_admin=0,
        )


if __name__ == "__main__":
    db.init_db()
    creer_admin_demo_si_vide()
    assurer_boucle()
    # host 0.0.0.0 pour tests ; debug=False avec le thread de jeu
    print("Serpentix prêt → http://127.0.0.1:5000")
    print("Comptes démo : admin / admin123  et  joueur2 / joueur2123")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
