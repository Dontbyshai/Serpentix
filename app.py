# -*- coding: utf-8 -*-
"""
app.py — Serveur web de Serpentix (Flask + Flask-SocketIO)
==========================================================

Rôle de ce fichier : c'est le « serveur web » du projet.
  - Il reçoit les requêtes HTTP du navigateur (pages, formulaires) et
    renvoie du HTML généré à partir des templates Jinja (dossier templates/).
  - Il valide les données côté SERVEUR (on ne fait jamais confiance au
    navigateur, la validation JavaScript peut être contournée).
  - Il appelle database.py pour lire / écrire dans SQLite.
  - Il fait tourner les parties multijoueur (2 ou 3 joueurs) en temps réel
    avec Socket.IO (WebSocket : connexion qui reste ouverte, le serveur peut
    « pousser » l'état du jeu plusieurs fois par seconde sans que le client
    redemande).

Lancement :  python app.py   puis   http://127.0.0.1:5000
Comptes   :  python app.py --comptes   crée les comptes Shai et noah
             s'ils n'existent pas encore (sans rien effacer).
"""

import hmac
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, jsonify,
)
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash

import database as db
from game_engine import (
    PartieEnCours, generer_code, code_valide, TICKS_PAR_SECONDE,
    JOUEURS_POSSIBLES, BONUS, reglages_client,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)


def charger_cle_secrete():
    """
    Retourne la clé qui SIGNE les cookies de session.

    Pourquoi c'est important : Flask stocke la session (dont user_id) dans un
    cookie signé. Si quelqu'un connaît la clé, il peut fabriquer un cookie
    « user_id = 1 » et se connecter sur n'importe quel compte.
    Ordre : variable d'environnement SERPENTIX_SECRET_KEY, sinon un fichier
    .secret_key généré au hasard au premier lancement (ignoré par git).
    """
    cle = os.environ.get("SERPENTIX_SECRET_KEY")
    if cle:
        return cle
    chemin = os.path.join(db.DOSSIER, ".secret_key")
    if os.path.exists(chemin):
        with open(chemin, "r", encoding="utf-8") as f:
            return f.read().strip()
    cle = secrets.token_hex(32)
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(cle)
    return cle


app.config["SECRET_KEY"] = charger_cle_secrete()
# Lax : le navigateur n'envoie pas le cookie de session quand un AUTRE site
# soumet un formulaire vers Serpentix (protection CSRF de base).
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True  # cookie illisible en JavaScript

# Socket.IO en mode « threading » (pas besoin de serveur spécial).
# Sans cors_allowed_origins="*" : seules les pages servies par CE site peuvent
# ouvrir une connexion temps réel.
socketio = SocketIO(app, async_mode="threading")

# Parties en cours, en mémoire : {code: PartieEnCours}. Le verrou (Lock) évite que
# le thread de jeu et une requête modifient la même partie au même moment.
PARTIES = {}
PARTIES_LOCK = threading.Lock()
_boucle_demarree = False
TICK_INTERVAL = 1 / TICKS_PAR_SECONDE   # durée d'un tick (1/7 s ≈ 0,14 s)

# Fiche de chaque bonus, affichée sur les pages de jeu et dans la doc.
# L'ordre de ce dictionnaire est l'ordre d'affichage de la légende.
BONUS_INFOS = {
    "turbo": ("Turbo", "Avance 2 fois plus vite pendant 3 s."),
    "bouclier": ("Bouclier", "Annule un choc mortel (le serpent recule et tourne)."),
    "fantome": ("Fantôme", "Traverse les corps pendant 4 s (pas les murs)."),
    "aimant": ("Aimant", "Attire les pommes proches pendant 6 s."),
    "ciseaux": ("Ciseaux", "Coupe la moitié de la queue de l'ennemi le plus proche."),
    "gel": ("Gel", "Ralentit tous les adversaires pendant 3 s."),
}

# Comptes de joueurs demandés pour la classe (mot de passe 1234).
# Ils sont créés directement par le serveur avec un hash Werkzeug : la règle
# « 6 caractères minimum » reste appliquée aux inscriptions par formulaire.
COMPTES_DE_BASE = (("Shai", "1234"), ("noah", "1234"))

# --- Anti-triche du mode solo (voir api_solo_debut / api_solo_fin) ---------
SOLO_COINS_MAX = 80             # plafond de coins par partie solo
SOLO_POMMES_PAR_SECONDE = 1.5   # au-delà, le score est physiquement impossible
SOLO_EN_COURS = {}              # {user_id: heure de début}, gardé côté SERVEUR
SOLO_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Validation côté serveur (les mêmes règles existent en JS dans validation.js)
# ---------------------------------------------------------------------------

def valider_pseudo(pseudo):
    """
    Paramètre : pseudo (str).
    Retour    : None si valide, sinon le message d'erreur (str).
    Règle : 3 à 20 caractères, lettres / chiffres / _ / - uniquement (ce qui
    interdit aussi les balises HTML et les espaces).
    """
    if not pseudo or not isinstance(pseudo, str):
        return "Le pseudo est obligatoire."
    pseudo = pseudo.strip()
    if len(pseudo) < 3 or len(pseudo) > 20:
        return "Le pseudo doit faire entre 3 et 20 caractères."
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", pseudo):
        return "Le pseudo ne peut contenir que lettres, chiffres, _ et -."
    return None


def valider_email(email):
    """
    Paramètre : email (str). Retour : None si valide, sinon message.
    Expression régulière simple : « quelque-chose @ quelque-chose . quelque-chose ».
    """
    if not email or not isinstance(email, str):
        return "L'e-mail est obligatoire."
    email = email.strip()
    if len(email) > 100:
        return "E-mail trop long."
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return "Format d'e-mail invalide."
    return None


def valider_mot_de_passe(mdp, obligatoire=True):
    """
    Paramètres : mdp (str), obligatoire (bool).
    Retour     : None si valide, sinon message. Longueur 6 à 100.
    """
    if not mdp:
        return "Le mot de passe est obligatoire." if obligatoire else None
    if len(mdp) < 6:
        return "Le mot de passe doit contenir au moins 6 caractères."
    if len(mdp) > 100:
        return "Mot de passe trop long."
    return None


def lien_interne(cible):
    """
    Paramètre : cible (str) — valeur du paramètre ?next= après connexion.
    Retour    : la cible si c'est un chemin du site (« /boutique »), sinon None.
    Empêche une « redirection ouverte » : un lien piégé
    /connexion?next=https://site-pirate.fr renverrait sinon la victime
    vers un faux site juste après sa connexion.
    """
    if cible and cible.startswith("/") and not cible.startswith("//") and "\\" not in cible:
        return cible
    return None


def utilisateur_connecte():
    """Retour : dict de l'utilisateur dont l'id est dans la session, ou None."""
    uid = session.get("user_id")
    if not uid:
        return None
    return db.obtenir_utilisateur(uid)


def login_requis(f):
    """
    Décorateur : placé au-dessus d'une route, il redirige vers /connexion
    si personne n'est connecté (et revient ensuite à la page demandée).
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not utilisateur_connecte():
            flash("Connecte-toi pour accéder à cette page.", "warning")
            return redirect(url_for("connexion", next=request.path))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Protection CSRF (Cross-Site Request Forgery)
# ---------------------------------------------------------------------------
# Principe : chaque session reçoit un jeton secret aléatoire. Chaque formulaire
# le renvoie dans un champ caché, chaque fetch() dans l'en-tête X-CSRF-Token.
# Un site pirate ne connaît pas ce jeton : il ne peut donc pas faire supprimer
# ton compte ou dépenser tes coins à ta place en t'envoyant un formulaire.

def jeton_csrf():
    """Retour : le jeton CSRF de la session (créé au premier appel)."""
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


@app.before_request
def verifier_csrf():
    """Exécutée AVANT chaque requête : refuse tout POST sans le bon jeton."""
    if request.method != "POST":
        return None
    envoye = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""
    attendu = session.get("csrf") or ""
    # compare_digest : comparaison en temps constant (bonne pratique)
    if attendu and hmac.compare_digest(envoye, attendu):
        return None
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "erreur": "Jeton de sécurité invalide, recharge la page."}), 400
    flash("Formulaire expiré, réessaie.", "warning")
    return redirect(request.path)


@app.context_processor
def inject_globals():
    """Variables disponibles dans TOUS les templates."""
    return {
        "current_user": utilisateur_connecte(),
        "SKINS": db.SKINS,
        "csrf_token": jeton_csrf,
        "BONUS_INFOS": BONUS_INFOS,
    }


# ---------------------------------------------------------------------------
# Boucle de jeu (thread qui « tique » TICKS_PAR_SECONDE fois par seconde)
# ---------------------------------------------------------------------------

def cloturer_partie(code, partie):
    """
    Enregistre une seule fois le résultat d'une partie finie dans SQLite,
    puis la retire de la mémoire (sinon PARTIES grossirait indéfiniment).
    Paramètres : code (str), partie (PartieEnCours). À appeler SANS le verrou.
    """
    with PARTIES_LOCK:
        if partie.enregistree:
            return
        partie.enregistree = True
        etat = partie.etat_public()
        scores = partie.scores_par_id()
        PARTIES.pop(code, None)
    if partie.partie_db_id:
        try:
            db.terminer_partie(partie.partie_db_id, etat.get("vainqueur_id"), scores)
        except sqlite3.Error as exc:
            app.logger.error("Erreur sauvegarde partie %s : %s", code, exc)


def boucle_jeu():
    """
    Thread « démon » (s'arrête avec le programme) : avance toutes les parties
    en cours puis envoie l'état à la « room » Socket.IO de chaque partie.
    L'envoi se fait HORS du verrou pour ne pas bloquer les autres joueurs.
    """
    while True:
        debut = time.time()
        with PARTIES_LOCK:
            en_cours = [(c, p) for c, p in PARTIES.items() if p.statut == "en_cours"]
        for code, partie in en_cours:
            with PARTIES_LOCK:
                finie = partie.tick()
                etat = partie.etat_public()
            socketio.emit("etat_jeu", etat, room=code)
            if finie:
                cloturer_partie(code, partie)
        # On dort le temps restant pour garder un rythme régulier
        time.sleep(max(0.0, TICK_INTERVAL - (time.time() - debut)))


def assurer_boucle():
    """Démarre le thread de jeu une seule fois."""
    global _boucle_demarree
    if not _boucle_demarree:
        threading.Thread(target=boucle_jeu, daemon=True).start()
        _boucle_demarree = True


def partie_depuis_code(code):
    """
    Retourne la partie en mémoire, ou la recrée depuis la BDD si la salle
    existe encore « en attente » (cas d'un serveur redémarré ou d'une page
    rechargée par le créateur). À appeler AVEC le verrou.
    Retour : PartieEnCours ou None.
    """
    partie = PARTIES.get(code)
    if partie:
        return partie
    row = db.obtenir_partie_par_code(code)
    if row and row["statut"] == "attente":
        partie = PartieEnCours(code, partie_db_id=row["id"],
                               max_joueurs=row.get("nb_joueurs") or 2)
        PARTIES[code] = partie
    return partie


# ---------------------------------------------------------------------------
# Routes HTML (pages)
# ---------------------------------------------------------------------------

@app.route("/")
def accueil():
    """Page d'accueil : présentation du jeu + gros bouton Jouer."""
    return render_template("accueil.html")


@app.route("/inscription", methods=["GET", "POST"])
def inscription():
    """
    CREATE — formulaire d'inscription.
    GET  : affiche le formulaire vide.
    POST : valide les champs ; si tout est bon, insère l'utilisateur en base,
           le connecte et l'envoie vers /jouer ; sinon réaffiche les erreurs.
    """
    if utilisateur_connecte():
        return redirect(url_for("jouer"))

    erreurs = {}
    valeurs = {"pseudo": "", "email": ""}

    if request.method == "POST":
        pseudo = (request.form.get("pseudo") or "").strip()
        email = (request.form.get("email") or "").strip()
        mdp = request.form.get("mot_de_passe") or ""
        mdp2 = request.form.get("mot_de_passe2") or ""
        valeurs = {"pseudo": pseudo, "email": email}  # pour pré-remplir

        for champ, erreur in (("pseudo", valider_pseudo(pseudo)),
                              ("email", valider_email(email)),
                              ("mot_de_passe", valider_mot_de_passe(mdp))):
            if erreur:
                erreurs[champ] = erreur
        if mdp != mdp2:
            erreurs["mot_de_passe2"] = "Les mots de passe ne correspondent pas."
        if "pseudo" not in erreurs and db.obtenir_par_pseudo(pseudo):
            erreurs["pseudo"] = "Ce pseudo est déjà pris."
        if "email" not in erreurs and db.obtenir_par_email(email):
            erreurs["email"] = "Cet e-mail est déjà utilisé."

        if not erreurs:
            try:
                # On stocke un HASH (empreinte) du mot de passe, jamais le mot de passe
                uid = db.creer_utilisateur(
                    pseudo, email, generate_password_hash(mdp),
                    couleur_skin="#ffffff", est_admin=0, coins=0, skins_debloques="blanc",
                )
            except sqlite3.IntegrityError:
                # Deux inscriptions identiques au même instant : UNIQUE a protégé la base
                erreurs["pseudo"] = "Ce pseudo ou cet e-mail vient d'être pris."
            else:
                session.clear()
                session["user_id"] = uid
                flash(f"Bienvenue {pseudo} ! Prêt à jouer.", "success")
                return redirect(url_for("jouer"))

    return render_template("inscription.html", erreurs=erreurs, valeurs=valeurs)


@app.route("/connexion", methods=["GET", "POST"])
def connexion():
    """
    Connexion : compare le mot de passe tapé avec le hash stocké
    (check_password_hash). Message volontairement vague (« pseudo OU mot de
    passe incorrect ») pour ne pas révéler quels pseudos existent.
    """
    if utilisateur_connecte():
        return redirect(url_for("jouer"))

    erreur = None
    pseudo = ""
    if request.method == "POST":
        pseudo = (request.form.get("pseudo") or "").strip()
        mdp = request.form.get("mot_de_passe") or ""
        user = db.obtenir_par_pseudo(pseudo) if pseudo else None
        if not user or not check_password_hash(user["mot_de_passe_hash"], mdp):
            erreur = "Pseudo ou mot de passe incorrect."
        else:
            session.clear()  # nouvelle session propre (nouveau jeton CSRF)
            session["user_id"] = user["id"]
            flash(f"Bon retour, {user['pseudo']} !", "success")
            return redirect(lien_interne(request.args.get("next")) or url_for("jouer"))

    return render_template("connexion.html", erreur=erreur, pseudo=pseudo)


@app.route("/deconnexion")
def deconnexion():
    """Vide la session (l'utilisateur n'est plus connecté)."""
    session.clear()
    flash("À bientôt.", "info")
    return redirect(url_for("accueil"))


@app.route("/profil", methods=["GET", "POST"])
@login_requis
def profil():
    """
    UPDATE de son propre profil (e-mail, mot de passe) + historique des parties.
    Le mot de passe n'est changé que si les deux champs sont remplis et égaux.
    """
    user = utilisateur_connecte()
    erreurs = {}

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        mdp = request.form.get("mot_de_passe") or ""
        mdp2 = request.form.get("mot_de_passe2") or ""

        e = valider_email(email)
        if e:
            erreurs["email"] = e
        else:
            autre = db.obtenir_par_email(email)
            if autre and autre["id"] != user["id"]:
                erreurs["email"] = "Cet e-mail est déjà utilisé."

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
            try:
                db.mettre_a_jour_utilisateur(user["id"], email=email,
                                             mot_de_passe_hash=nouveau_hash)
            except sqlite3.IntegrityError:
                erreurs["email"] = "Cet e-mail est déjà utilisé."
            else:
                flash("Profil mis à jour.", "success")
                return redirect(url_for("profil"))

    histo = db.historique_utilisateur(user["id"])
    return render_template("profil.html", user=user, erreurs=erreurs, historique=histo)


@app.route("/boutique", methods=["GET", "POST"])
@login_requis
def boutique():
    """
    Boutique de skins.
    POST action=acheter : débloque un skin (débit des coins en SQL).
    POST action=equiper : équipe un skin déjà possédé.
    Après un POST on redirige (modèle « Post/Redirect/Get ») : un F5 ne
    renvoie pas le formulaire une 2e fois.
    """
    user = utilisateur_connecte()

    if request.method == "POST":
        action = request.form.get("action")
        skin_id = (request.form.get("skin_id") or "").strip().lower()
        if action == "acheter":
            ok, msg, _ = db.acheter_skin(user["id"], skin_id)
        elif action == "equiper":
            ok, msg, _ = db.equiper_skin(user["id"], skin_id)
        else:
            ok, msg = False, "Action inconnue."
        flash(msg, "success" if ok else "warning")
        return redirect(url_for("boutique"))

    return render_template("boutique.html", user=user, skins=db.SKINS,
                           equipe=db.skin_id_depuis_hex(user["couleur_skin"]))


@app.route("/classement")
def classement():
    """
    READ collectif : classement calculé en SQL (voir database.classement).
    Paramètre d'URL ?tri=victoires|ratio|score|coins. Une valeur inconnue
    (ou piégée) est remplacée par « victoires » : validation côté serveur.
    """
    tri = request.args.get("tri", "victoires")
    if tri not in db.TRIS_CLASSEMENT:
        tri = "victoires"
    lignes = db.classement(tri=tri, limit=50)
    moi = utilisateur_connecte()
    # Position du joueur connecté (pour la mettre en évidence)
    ma_ligne = None
    if moi:
        for rang, ligne in enumerate(lignes, start=1):
            if ligne["id"] == moi["id"]:
                ma_ligne = {**ligne, "rang": rang}
    return render_template("classement.html", classement=lignes, tri=tri,
                           podium=lignes[:3], ma_ligne=ma_ligne)


@app.route("/jouer")
@login_requis
def jouer():
    """Hub de jeu : Solo, ou multijoueur à 2 ou 3 (créer une salle / rejoindre avec un code)."""
    return render_template("lobby.html")


@app.route("/partie/<code>")
@login_requis
def partie(code):
    """Page canvas d'une salle multijoueur. Le code est vérifié avant affichage."""
    code = code.upper()
    if not code_valide(code):
        flash("Code de salle invalide.", "warning")
        return redirect(url_for("jouer"))
    # Durée en secondes de chaque effet minuté (pour les barres du HUD)
    durees = {nom: info["duree"] / TICKS_PAR_SECONDE
              for nom, info in BONUS.items() if info["duree"]}
    return render_template("partie.html", code=code, durees=durees)


@app.route("/solo")
@login_requis
def solo():
    """Mode solo : la partie tourne dans le navigateur (solo.js)."""
    # reglages_client() : vitesse, durées des bonus… lues dans game_engine.py
    return render_template("solo.html", couleur=utilisateur_connecte()["couleur_skin"],
                           reglages=reglages_client())


# ---------------------------------------------------------------------------
# CRUD utilisateurs — exigence NSI (lien dans le pied de page)
# ---------------------------------------------------------------------------

@app.route("/utilisateurs")
@login_requis
def liste_utilisateurs():
    """READ collectif : tableau de tous les utilisateurs."""
    return render_template("utilisateurs_liste.html", utilisateurs=db.lister_utilisateurs())


@app.route("/utilisateurs/<int:uid>")
@login_requis
def detail_utilisateur(uid):
    """READ individuel : fiche d'un utilisateur + ses dernières parties."""
    user = db.obtenir_utilisateur(uid)
    if not user:
        flash("Utilisateur introuvable.", "danger")
        return redirect(url_for("liste_utilisateurs"))
    return render_template("utilisateur_detail.html", user=user,
                           historique=db.historique_utilisateur(uid))


@app.route("/utilisateurs/<int:uid>/modifier", methods=["GET", "POST"])
@login_requis
def modifier_utilisateur(uid):
    """
    UPDATE : modifier pseudo / e-mail / mot de passe.
    Sécurité serveur : on ne peut modifier QUE son propre compte (même en
    tapant l'URL d'un autre id à la main).
    """
    courant = utilisateur_connecte()
    if courant["id"] != uid:
        flash("Tu ne peux modifier que ton propre compte.", "danger")
        return redirect(url_for("liste_utilisateurs"))
    user = courant

    erreurs = {}
    if request.method == "POST":
        pseudo = (request.form.get("pseudo") or "").strip()
        email = (request.form.get("email") or "").strip()
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

        nouveau_hash = None
        if mdp:  # champ vide = mot de passe inchangé
            e = valider_mot_de_passe(mdp)
            if e:
                erreurs["mot_de_passe"] = e
            else:
                nouveau_hash = generate_password_hash(mdp)

        if not erreurs:
            try:
                db.mettre_a_jour_utilisateur(uid, pseudo=pseudo, email=email,
                                             mot_de_passe_hash=nouveau_hash)
            except sqlite3.IntegrityError:
                erreurs["pseudo"] = "Pseudo ou e-mail déjà utilisé."
            else:
                flash("Compte mis à jour.", "success")
                return redirect(url_for("detail_utilisateur", uid=uid))

        user = {**user, "pseudo": pseudo, "email": email}  # réafficher la saisie

    return render_template("utilisateur_modifier.html", user=user, erreurs=erreurs)


@app.route("/utilisateurs/<int:uid>/supprimer", methods=["POST"])
@login_requis
def supprimer_utilisateur(uid):
    """
    DELETE : bouton « Supprimer » (méthode POST uniquement, jamais GET, pour
    qu'un simple lien ne puisse pas effacer un compte). Seulement son compte.
    """
    courant = utilisateur_connecte()
    if courant["id"] != uid:
        flash("Suppression non autorisée.", "danger")
        return redirect(url_for("liste_utilisateurs"))
    db.supprimer_utilisateur(uid)
    session.clear()
    flash("Ton compte a été supprimé.", "info")
    return redirect(url_for("accueil"))


@app.route("/utilisateurs/nouveau", methods=["GET", "POST"])
@login_requis
def nouvel_utilisateur():
    """CREATE via le formulaire de gestion : ajoute un joueur (skin blanc, 0 coin)."""
    erreurs = {}
    valeurs = {"pseudo": "", "email": ""}

    if request.method == "POST":
        pseudo = (request.form.get("pseudo") or "").strip()
        email = (request.form.get("email") or "").strip()
        mdp = request.form.get("mot_de_passe") or ""
        valeurs = {"pseudo": pseudo, "email": email}

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

        if not erreurs:
            try:
                db.creer_utilisateur(pseudo, email, generate_password_hash(mdp),
                                     "#ffffff", 0, 0, "blanc")
            except sqlite3.IntegrityError:
                erreurs["pseudo"] = "Pseudo ou e-mail déjà utilisé."
            else:
                flash(f"Joueur {pseudo} créé.", "success")
                return redirect(url_for("liste_utilisateurs"))

    return render_template("utilisateur_nouveau.html", erreurs=erreurs, valeurs=valeurs)


# ---------------------------------------------------------------------------
# API JSON (appelées en JavaScript avec fetch)
# ---------------------------------------------------------------------------

@app.route("/api/partie/creer", methods=["POST"])
@login_requis
def api_creer_partie():
    """
    Crée une salle : code unique + ligne dans la table parties.
    Corps JSON : {"nb_joueurs": 2 ou 3} (taille de la salle).
    Retour JSON : {"ok": true, "code": "ABC123", "nb_joueurs": 3}.
    """
    user = utilisateur_connecte()
    data = request.get_json(silent=True) or {}
    # Validation SERVEUR : seuls 2 et 3 sont acceptés (la page ne propose que
    # ces deux choix, mais une requête peut être fabriquée à la main)
    try:
        nb_joueurs = int(data.get("nb_joueurs", 2))
    except (TypeError, ValueError):
        nb_joueurs = 0
    if nb_joueurs not in JOUEURS_POSSIBLES:
        return jsonify({"ok": False, "erreur": "Choisis 2 ou 3 joueurs."}), 400
    for _ in range(20):  # on retire un code tant qu'il est déjà utilisé
        code = generer_code()
        if code not in PARTIES and not db.obtenir_partie_par_code(code):
            break
    else:
        return jsonify({"ok": False, "erreur": "Impossible de générer un code."}), 500

    partie_id = db.creer_partie(code, user["id"], nb_joueurs)
    with PARTIES_LOCK:
        PARTIES[code] = PartieEnCours(code, partie_db_id=partie_id, max_joueurs=nb_joueurs)
    assurer_boucle()
    return jsonify({"ok": True, "code": code, "nb_joueurs": nb_joueurs})


@app.route("/api/partie/rejoindre", methods=["POST"])
@login_requis
def api_rejoindre_partie():
    """
    Vérifie qu'une salle existe, attend encore des joueurs et a de la place.
    Corps JSON : {"code": "ABC123"}. Retour : {"ok": bool, "code" | "erreur"}.
    """
    data = request.get_json(silent=True) or {}
    code = str(data.get("code") or "").strip().upper()
    if not code_valide(code):
        return jsonify({"ok": False, "erreur": "Le code fait 6 lettres ou chiffres."}), 400

    user = utilisateur_connecte()
    with PARTIES_LOCK:
        partie = partie_depuis_code(code)
        if not partie or partie.statut != "attente":
            return jsonify({"ok": False, "erreur": "Partie introuvable ou déjà commencée."}), 404
        deja_dedans = any(s.joueur_id == user["id"] for s in partie.joueurs.values())
        if len(partie.ordre_sids) >= partie.max_joueurs and not deja_dedans:
            return jsonify({"ok": False,
                            "erreur": f"Partie pleine ({partie.max_joueurs} joueurs max)."}), 400
        partie_db_id = partie.partie_db_id

    if partie_db_id:
        db.ajouter_participant(partie_db_id, user["id"])
    assurer_boucle()
    return jsonify({"ok": True, "code": code})


@app.route("/api/solo/debut", methods=["POST"])
@login_requis
def api_solo_debut():
    """
    Le navigateur prévient le serveur qu'une partie solo commence.
    Le serveur note l'heure de début DANS SA MÉMOIRE (pas dans un cookie que
    le joueur pourrait recopier). Retour JSON : {"ok": true}.
    """
    with SOLO_LOCK:
        SOLO_EN_COURS[utilisateur_connecte()["id"]] = time.time()
    return jsonify({"ok": True})


@app.route("/api/solo/fin", methods=["POST"])
@login_requis
def api_solo_fin():
    """
    Crédite les coins d'une partie solo. Corps JSON : {"score": int}.

    Le solo tourne dans le navigateur, donc le score envoyé PEUT être faux
    (n'importe qui peut envoyer {"score": 999} avec la console). Trois
    vérifications simples côté serveur limitent la triche :
      1) il faut avoir appelé /api/solo/debut avant → sinon refus ;
      2) une partie n'est payée qu'UNE fois (on efface l'heure de début) ;
      3) le score ne peut pas dépasser ce qui est faisable dans la durée
         réelle de la partie (SOLO_POMMES_PAR_SECONDE), ni SOLO_COINS_MAX.
    Retour JSON : {"ok", "gain", "coins", "ajuste"}.
    """
    user = utilisateur_connecte()
    data = request.get_json(silent=True) or {}
    try:
        score = max(0, int(data.get("score", 0)))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "erreur": "Score invalide."}), 400

    with SOLO_LOCK:
        debut = SOLO_EN_COURS.pop(user["id"], None)
    if debut is None:
        return jsonify({"ok": False, "erreur": "Aucune partie solo en cours."}), 400

    duree = time.time() - debut
    score_possible = int(duree * SOLO_POMMES_PAR_SECONDE)
    gain = min(score, score_possible, SOLO_COINS_MAX)
    nouveau = db.ajouter_coins(user["id"], gain)
    return jsonify({"ok": True, "gain": gain, "coins": nouveau, "ajuste": gain < score})


# ---------------------------------------------------------------------------
# Socket.IO — événements temps réel des parties multijoueur
# ---------------------------------------------------------------------------
# Client → serveur : rejoindre_salle, direction, quitter_salle
# Serveur → client : etat_jeu, partie_lancee, erreur

def lire_code(data):
    """Extrait et normalise le code d'un message Socket.IO. Retour : str ou None."""
    if not isinstance(data, dict):
        return None
    code = str(data.get("code") or "").strip().upper()
    return code if code_valide(code) else None


@socketio.on("rejoindre_salle")
def on_rejoindre_salle(data):
    """
    Le navigateur entre dans la salle : on l'ajoute à la partie et à la
    « room » Socket.IO (groupe de connexions qui reçoivent le même état).
    Quand la salle est pleine (2 ou 3 joueurs selon le choix du créateur),
    la partie démarre (compte à rebours de 3 s).
    """
    user = utilisateur_connecte()  # la session Flask marche aussi en Socket.IO
    if not user:
        emit("erreur", {"message": "Non connecté."})
        return
    code = lire_code(data)
    if not code:
        emit("erreur", {"message": "Code invalide."})
        return

    with PARTIES_LOCK:
        partie = partie_depuis_code(code)
        if not partie:
            emit("erreur", {"message": "Salle introuvable ou terminée."})
            return
        ok, message = partie.ajouter_joueur(
            request.sid, user["id"], user["pseudo"], user["couleur_skin"]
        )
        if not ok:
            emit("erreur", {"message": message})
            return
        join_room(code)
        demarrer = partie.peut_demarrer()
        if demarrer:
            partie.demarrer()
        etat = partie.etat_public()
        partie_db_id = partie.partie_db_id
        ids_joueurs = [s.joueur_id for s in partie.joueurs.values()]

    if demarrer and partie_db_id:
        # Chaque joueur présent a sa ligne dans participations (2 ou 3 lignes)
        for uid in ids_joueurs:
            db.ajouter_participant(partie_db_id, uid)
        db.demarrer_partie(partie_db_id)
    emit("etat_jeu", etat, room=code)
    if demarrer:
        emit("partie_lancee", {"code": code}, room=code)


@socketio.on("direction")
def on_direction(data):
    """Reçoit un virage {"code", "dx", "dy"} ; le moteur vérifie sa validité."""
    code = lire_code(data)
    if not code:
        return
    try:
        dx, dy = int(data.get("dx", 0)), int(data.get("dy", 0))
    except (TypeError, ValueError):
        return  # message mal formé : on l'ignore
    with PARTIES_LOCK:
        partie = PARTIES.get(code)
        if partie:
            partie.traiter_direction(request.sid, dx, dy)


def depart_joueur(sid, codes):
    """
    Retire la connexion sid des parties indiquées et prévient les autres joueurs.
    Paramètres : sid (str), codes (liste de codes de salle).
    """
    a_notifier, a_cloturer = [], []
    with PARTIES_LOCK:
        for code in codes:
            partie = PARTIES.get(code)
            if not partie or sid not in partie.joueurs:
                continue
            fin = partie.retirer_joueur(sid)
            a_notifier.append((code, partie.etat_public()))
            if fin:
                a_cloturer.append((code, partie))
            elif partie.statut == "attente" and not partie.ordre_sids:
                PARTIES.pop(code, None)  # salle vide : la BDD la garde « en attente »
    for code, etat in a_notifier:
        socketio.emit("etat_jeu", etat, room=code)
    for code, partie in a_cloturer:
        cloturer_partie(code, partie)  # victoire par forfait enregistrée


@socketio.on("quitter_salle")
def on_quitter_salle(data):
    """Le joueur clique « Quitter » ou ferme l'onglet."""
    code = lire_code(data)
    if code:
        depart_joueur(request.sid, [code])
        leave_room(code)


@socketio.on("disconnect")
def on_disconnect(*args):
    """Connexion perdue (réseau, onglet fermé) : même traitement que quitter."""
    with PARTIES_LOCK:
        codes = [c for c, p in PARTIES.items() if request.sid in p.joueurs]
    depart_joueur(request.sid, codes)


# ---------------------------------------------------------------------------
# Démarrage
# ---------------------------------------------------------------------------

def creer_comptes_de_base():
    """
    Crée les comptes de COMPTES_DE_BASE (Shai, noah) s'ils n'existent
    pas encore. Ne supprime et ne modifie RIEN : un compte déjà présent (même
    pseudo, sans tenir compte des majuscules) est laissé tel quel.
    Passe par les fonctions normales du projet : db.creer_utilisateur() et
    generate_password_hash() (le mot de passe n'est jamais stocké en clair).
    Retour : liste des pseudos créés.
    """
    crees = []
    for pseudo, mdp in COMPTES_DE_BASE:
        if db.obtenir_par_pseudo(pseudo):
            continue
        try:
            db.creer_utilisateur(pseudo, f"{pseudo.lower()}@serpentix.local",
                                 generate_password_hash(mdp), "#ffffff",
                                 est_admin=0, coins=100, skins_debloques="blanc")
            crees.append(pseudo)
        except sqlite3.IntegrityError:
            pass  # e-mail déjà pris par un autre compte : on n'écrase rien
    return crees


if __name__ == "__main__":
    db.init_db()
    if "--comptes" in sys.argv:
        # Utilisation : python app.py --comptes  (puis le programme s'arrête)
        print("Comptes créés :", ", ".join(creer_comptes_de_base()) or "aucun (déjà là)")
        sys.exit(0)
    if not db.lister_utilisateurs():
        # Base toute neuve : on crée les comptes de la classe
        creer_comptes_de_base()
    assurer_boucle()
    host = os.environ.get("SERPENTIX_HOST", "0.0.0.0")
    port = int(os.environ.get("SERPENTIX_PORT", "5000"))
    print(f"Serpentix prêt → http://{host}:{port}")
    print("Comptes : Shai / 1234, noah / 1234")
    # allow_unsafe_werkzeug : serveur de développement, suffisant pour un projet scolaire
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)
