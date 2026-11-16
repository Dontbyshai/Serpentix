# -*- coding: utf-8 -*-
"""
test_classement.py — Tests des deux classements (unittest).

On vérifie la requête SQL du classement INDIVIDUEL (database.classement_individuel)
et on contrôle que le classement DE GROUPE (database.classement) et la route
/classement gardent le même sens qu'avant.

Chaque test utilise une base SQLite temporaire : le fichier serpentix.db
du projet n'est ni lu ni modifié.

Lancement (depuis le dossier du projet) :
    python -m unittest discover tests
"""

import os
import sys
import tempfile
import unittest

# Le dossier du projet est le parent de tests/ : on peut importer database et app.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db  # noqa: E402
import app as serveur  # noqa: E402


class TestClassement(unittest.TestCase):
    """Stats SQL et pages /classement et /classement/individuel."""

    def setUp(self):
        """Crée une base vide dans un dossier temporaire et l'active."""
        self._dossier = tempfile.TemporaryDirectory()
        self._ancien_chemin = db.DB_PATH
        # database.py et app.py partagent le même module : changer DB_PATH
        # suffit pour que les deux parlent à la base de test.
        db.DB_PATH = os.path.join(self._dossier.name, "test_classement.db")
        db.init_db()

    def tearDown(self):
        """Remet le chemin de la vraie base et supprime le dossier temporaire."""
        db.DB_PATH = self._ancien_chemin
        self._dossier.cleanup()

    def _joueur(self, pseudo, coins=0, couleur="#ffffff"):
        """
        Insère un compte de test.

        Paramètres : pseudo (str), coins (int), couleur (hex du skin).
        Retour     : int — id du joueur.
        """
        return db.creer_utilisateur(
            pseudo, f"{pseudo.lower()}@test.local", "hash-de-test",
            couleur_skin=couleur, coins=coins,
        )

    def _partie(self, code, ids, vainqueur, scores, statut="terminee"):
        """
        Crée une partie et, si demandé, la clôture.

        Paramètres :
          code (str)       — code de salle, unique dans ce test
          ids (list[int])  — joueurs, le premier est le créateur (2 ou 3)
          vainqueur (int ou None) — None = match nul
          scores (dict)    — {id_joueur: score}
          statut (str)     — "terminee", "en_cours" ou "attente"
        Retour : int — id de la partie.
        """
        partie_id = db.creer_partie(code, ids[0], len(ids))
        for uid in ids[1:]:
            db.ajouter_participant(partie_id, uid)
        if statut == "en_cours":
            db.demarrer_partie(partie_id)
        elif statut == "terminee":
            db.terminer_partie(partie_id, vainqueur, scores)
        return partie_id

    def _par_pseudo(self, lignes):
        """Paramètre : liste de dict du classement. Retour : dict {pseudo: ligne}."""
        return {ligne["pseudo"]: ligne for ligne in lignes}

    def test_compte_sans_partie_apparait_a_zero(self):
        """Un joueur inscrit qui n'a jamais joué est quand même dans le classement."""
        self._joueur("Seul")
        lignes = db.classement_individuel()
        self.assertEqual(len(lignes), 1)
        joueur = lignes[0]
        self.assertEqual(joueur["pseudo"], "Seul")
        self.assertEqual(joueur["parties_jouees"], 0)
        self.assertEqual(joueur["victoires"], 0)
        self.assertEqual(joueur["nuls"], 0)
        self.assertEqual(joueur["defaites"], 0)
        self.assertEqual(float(joueur["ratio"]), 0.0)  # pas de division par zéro
        self.assertEqual(joueur["meilleur_score"], 0)

    def test_victoire_defaite_nul_et_ratio(self):
        """
        Victoire, défaite et nul d'un même joueur.
        1 victoire sur 3 parties → 33,3 % (arrondi SQL à 1 décimale).
        """
        alice = self._joueur("Alice")
        bob = self._joueur("Bob")
        # Alice gagne 4 à 1.
        self._partie("WIN001", [alice, bob], alice, {alice: 4, bob: 1})
        # Bob gagne 2 à 0 : défaite d'Alice.
        self._partie("LOS001", [alice, bob], bob, {alice: 0, bob: 2})
        # Match nul (vainqueur None) : les deux ont le drapeau a_gagne à 0.
        self._partie("NUL001", [alice, bob], None, {alice: 3, bob: 3})

        stats = self._par_pseudo(db.classement_individuel())
        self.assertEqual(stats["Alice"]["parties_jouees"], 3)
        self.assertEqual(stats["Alice"]["victoires"], 1)
        self.assertEqual(stats["Alice"]["nuls"], 1)
        self.assertEqual(stats["Alice"]["defaites"], 1)
        self.assertEqual(float(stats["Alice"]["ratio"]), 33.3)
        self.assertEqual(stats["Alice"]["meilleur_score"], 4)
        self.assertEqual(stats["Bob"]["victoires"], 1)
        self.assertEqual(stats["Bob"]["defaites"], 1)
        self.assertEqual(stats["Bob"]["meilleur_score"], 3)

    def test_partie_non_terminee_ignoree(self):
        """Une salle en attente ou en cours ne compte ni au score ni en victoire."""
        alice = self._joueur("Alice")
        bob = self._joueur("Bob")
        self._partie("WAIT01", [alice, bob], None, {}, statut="attente")
        partie = self._partie("RUN001", [alice, bob], None, {}, statut="en_cours")
        # Même si on écrivait un score « à la main », la partie non finie est ignorée.
        with db.db_cursor() as cur:
            cur.execute(
                "UPDATE participations SET score = 99, a_gagne = 1 WHERE partie_id = ?",
                (partie,),
            )
        self._partie("OK0001", [alice, bob], alice, {alice: 2, bob: 0})

        alice_stats = self._par_pseudo(db.classement_individuel())["Alice"]
        self.assertEqual(alice_stats["parties_jouees"], 1)
        self.assertEqual(alice_stats["victoires"], 1)
        self.assertEqual(alice_stats["meilleur_score"], 2)

    def test_trois_joueurs_et_coins(self):
        """À 3 joueurs : 1 victoire et 2 défaites. Les coins viennent du compte."""
        ada = self._joueur("Ada", coins=10, couleur="#ef4444")
        ben = self._joueur("Ben", coins=80, couleur="#22c55e")
        cio = self._joueur("Cio", coins=0, couleur="#eab308")
        self._partie(
            "TROIS1", [ada, ben, cio], ben, {ada: 1, ben: 6, cio: 2},
        )
        stats = self._par_pseudo(db.classement_individuel())
        self.assertEqual(stats["Ben"]["victoires"], 1)
        self.assertEqual(stats["Ben"]["defaites"], 0)
        self.assertEqual(stats["Ben"]["meilleur_score"], 6)
        self.assertEqual(stats["Ben"]["coins"], 80 + 6 + db.BONUS_VICTOIRE)
        self.assertEqual(stats["Ada"]["defaites"], 1)
        self.assertEqual(stats["Ada"]["coins"], 10 + 1)  # score, pas de bonus
        self.assertEqual(stats["Cio"]["parties_jouees"], 1)

    def test_tris_et_valeur_inconnue(self):
        """
        tri=defaites met le plus de défaites en premier.
        Une clé inconnue (ou un texte piégé) retombe sur le tri par victoires,
        sans erreur : le texte n'est pas collé dans le SQL.
        """
        faible = self._joueur("Faible")
        fort = self._joueur("Fort")
        # Faible perd deux fois, Fort gagne deux fois.
        self._partie("D1XXXX", [faible, fort], fort, {faible: 0, fort: 1})
        self._partie("D2XXXX", [faible, fort], fort, {faible: 0, fort: 1})

        par_defaites = db.classement_individuel(tri="defaites")
        self.assertEqual(par_defaites[0]["pseudo"], "Faible")
        self.assertEqual(par_defaites[0]["defaites"], 2)

        par_victoires = db.classement_individuel(tri="victoires")
        self.assertEqual(par_victoires[0]["pseudo"], "Fort")

        piege = db.classement_individuel(tri="victoires; DROP TABLE utilisateurs;--")
        self.assertEqual(piege[0]["pseudo"], "Fort")
        # La table est toujours là : la requête piégée n'a pas été exécutée.
        self.assertEqual(len(db.lister_utilisateurs()), 2)

    def test_limite(self):
        """limit coupe la liste après les premiers du tri."""
        self._joueur("A")
        self._joueur("B")
        self._joueur("C")
        self.assertEqual(len(db.classement_individuel(limit=2)), 2)

    def test_groupe_et_individuel_daccord_puis_distincts(self):
        """
        Sur des parties normales, les deux classements donnent les mêmes
        victoires (le drapeau a_gagne est posé à partir du vainqueur).

        Si on modifie SEULEMENT a_gagne, le classement individuel change et
        le classement de groupe non : chacun lit bien sa propre colonne.
        """
        alice = self._joueur("Alice")
        bob = self._joueur("Bob")
        self._partie("SAME01", [alice, bob], alice, {alice: 5, bob: 1})

        groupe = self._par_pseudo(db.classement())
        individuel = self._par_pseudo(db.classement_individuel())
        self.assertEqual(groupe["Alice"]["victoires"], 1)
        self.assertEqual(individuel["Alice"]["victoires"], 1)
        self.assertEqual(groupe["Bob"]["defaites"], 1)
        self.assertEqual(individuel["Bob"]["defaites"], 1)

        # On inverse le drapeau personnel, sans toucher au vainqueur de la partie.
        with db.db_cursor() as cur:
            cur.execute("UPDATE participations SET a_gagne = 0 WHERE utilisateur_id = ?", (alice,))
            cur.execute("UPDATE participations SET a_gagne = 1 WHERE utilisateur_id = ?", (bob,))

        groupe = self._par_pseudo(db.classement())
        individuel = self._par_pseudo(db.classement_individuel())
        self.assertEqual(groupe["Alice"]["victoires"], 1)       # lit parties.vainqueur_id
        self.assertEqual(individuel["Alice"]["victoires"], 0)   # lit participations.a_gagne
        self.assertEqual(individuel["Bob"]["victoires"], 1)
        self.assertEqual(groupe["Bob"]["victoires"], 0)

    def test_route_classement_de_groupe(self):
        """La page historique répond, garde ses onglets, et n'ajoute pas le tri « Nuls »."""
        self._joueur("Shai")
        reponse = serveur.app.test_client().get("/classement")
        self.assertEqual(reponse.status_code, 200)
        page = reponse.get_data(as_text=True)
        self.assertIn("Classement de groupe", page)
        self.assertIn("Classement individuel", page)  # le bouton pour basculer
        self.assertIn("% victoires", page)
        self.assertIn("Meilleur score", page)
        self.assertNotIn(">Nuls<", page)
        self.assertNotIn(">Défaites<", page)

    def test_route_classement_individuel(self):
        """
        La nouvelle route affiche les stats et respecte le tri par coins.
        Un ?tri= piégé ne provoque pas d'erreur 500.
        """
        self._joueur("Pauvre", coins=1)
        self._joueur("Riche", coins=50)
        client = serveur.app.test_client()

        page = client.get("/classement/individuel?tri=coins").get_data(as_text=True)
        self.assertIn("Classement individuel", page)
        self.assertIn(">Nuls<", page)
        self.assertIn(">Défaites<", page)
        self.assertIn("Riche", page)
        self.assertIn("Pauvre", page)
        # Dans le TABLEAU (pas le podium, qui affiche le 2e à gauche),
        # le tri par coins met Riche sur la première ligne.
        tableau = page.split("<tbody>", 1)[1]
        self.assertLess(tableau.index("Riche"), tableau.index("Pauvre"))

        piege = client.get("/classement/individuel?tri=1;DROP%20TABLE%20utilisateurs")
        self.assertEqual(piege.status_code, 200)
        self.assertEqual(len(db.lister_utilisateurs()), 2)

        # Un tri qui n'existe que pour l'individuel est ignoré sur la page de groupe.
        groupe = client.get("/classement?tri=defaites")
        self.assertEqual(groupe.status_code, 200)
        self.assertIn("Victoires", groupe.get_data(as_text=True))
