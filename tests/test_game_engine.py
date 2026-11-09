# -*- coding: utf-8 -*-
"""
test_game_engine.py — Tests automatiques des règles du jeu (module unittest).

Lancement (depuis le dossier du projet) :
    python -m unittest discover tests

Chaque test prépare une situation précise (positions des serpents), appelle
tick() et vérifie le résultat avec assert…. C'est la « validation des
programmes » demandée au programme de NSI : si on casse une règle en
modifiant le code, un test échoue tout de suite.
"""

import os
import sys
import unittest

# Permet d'importer game_engine.py qui est dans le dossier parent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_engine import PartieEnCours, Serpent, code_valide  # noqa: E402


def partie_prete():
    """Crée une partie à 2 joueurs, démarrée, sans pommes ni bonus ni décompte."""
    p = PartieEnCours("TEST01")
    p.ajouter_joueur("a", 1, "Alice", "#ffffff")
    p.ajouter_joueur("b", 2, "Bob", "#ef4444")
    p.demarrer()
    p.decompte = 0
    p.pommes, p.bonus = [], []
    p._placer_pommes = lambda: None   # on neutralise le placement aléatoire
    p._placer_bonus = lambda: None
    return p


def placer(p, sid, corps, direction):
    """Place le serpent sid avec un corps (tête en premier) et une direction."""
    s = p.joueurs[sid]
    s.corps = list(corps)
    s.direction = direction
    s.file_directions = []


class TestRegles(unittest.TestCase):

    def test_code_valide(self):
        self.assertTrue(code_valide("AB12CD"))
        self.assertFalse(code_valide("ab12cd"))   # minuscules refusées
        self.assertFalse(code_valide("AB12"))     # trop court
        self.assertFalse(code_valide("<scrip"))   # caractères interdits

    def test_demi_tour_interdit(self):
        s = Serpent(1, "x", "#fff", (10, 10), (1, 0))
        s.changer_direction(-1, 0)                # gauche alors qu'on va à droite
        self.assertEqual(s.file_directions, [])

    def test_file_de_virages(self):
        s = Serpent(1, "x", "#fff", (10, 10), (1, 0))
        s.changer_direction(0, -1)                # haut
        s.changer_direction(-1, 0)                # puis gauche (valide après haut)
        self.assertEqual(s.file_directions, [(0, -1), (-1, 0)])

    def test_mur_elimine(self):
        p = partie_prete()
        placer(p, "a", [(39, 5), (38, 5), (37, 5)], (1, 0))
        placer(p, "b", [(10, 20), (11, 20), (12, 20)], (-1, 0))
        self.assertTrue(p.tick())
        self.assertFalse(p.joueurs["a"].vivant)
        self.assertEqual(p.vainqueur_sid, "b")

    def test_tete_dans_le_corps_adverse(self):
        p = partie_prete()
        placer(p, "a", [(10, 9), (10, 8), (10, 7)], (0, 1))       # descend
        placer(p, "b", [(12, 10), (11, 10), (10, 10), (9, 10)], (1, 0))
        p.tick()
        self.assertFalse(p.joueurs["a"].vivant)
        self.assertTrue(p.joueurs["b"].vivant)

    def test_tete_contre_tete_egalite(self):
        p = partie_prete()
        placer(p, "a", [(10, 10), (9, 10), (8, 10)], (1, 0))
        placer(p, "b", [(12, 10), (13, 10), (14, 10)], (-1, 0))   # même case (11,10)
        p.tick()
        self.assertFalse(p.joueurs["a"].vivant)
        self.assertFalse(p.joueurs["b"].vivant)
        self.assertIn("nul", p.message_fin.lower())

    def test_tete_contre_tete_le_plus_long_gagne(self):
        p = partie_prete()
        placer(p, "a", [(10, 10), (9, 10), (8, 10), (7, 10)], (1, 0))  # 4 cases
        placer(p, "b", [(11, 10), (12, 10), (13, 10)], (-1, 0))        # croisement
        p.tick()
        self.assertTrue(p.joueurs["a"].vivant)
        self.assertFalse(p.joueurs["b"].vivant)

    def test_bouclier_annule_un_choc(self):
        p = partie_prete()
        placer(p, "a", [(39, 5), (38, 5), (37, 5)], (1, 0))
        placer(p, "b", [(10, 20), (11, 20), (12, 20)], (-1, 0))
        p.joueurs["a"].bouclier = True
        self.assertFalse(p.tick())                 # la partie continue
        a = p.joueurs["a"]
        self.assertTrue(a.vivant)
        self.assertFalse(a.bouclier)               # consommé
        self.assertIn(a.direction, [(0, -1), (0, 1)])  # a pivoté
        p.tick()
        self.assertTrue(a.vivant)                  # et ne retape pas le mur

    def test_turbo_ne_traverse_pas_un_corps(self):
        p = partie_prete()
        placer(p, "a", [(10, 10), (9, 10), (8, 10)], (1, 0))
        placer(p, "b", [(11, 12), (11, 11), (11, 10), (11, 9), (11, 8)], (0, 1))
        p.joueurs["a"].turbo_restant = 5
        p.tick()
        self.assertFalse(p.joueurs["a"].vivant)    # bloqué par le corps de b

    def test_pomme_fait_grandir(self):
        p = partie_prete()
        placer(p, "a", [(10, 10), (9, 10), (8, 10)], (1, 0))
        placer(p, "b", [(10, 20), (11, 20), (12, 20)], (-1, 0))
        p.pommes = [(11, 10)]
        p.tick()
        p.tick()
        a = p.joueurs["a"]
        self.assertEqual(a.score, 1)
        self.assertEqual(len(a.corps), 4)

    def test_meme_compte_deux_fois(self):
        p = PartieEnCours("TEST02")
        p.ajouter_joueur("onglet1", 1, "Alice", "#fff")
        p.ajouter_joueur("onglet2", 1, "Alice", "#fff")   # même compte
        self.assertEqual(len(p.ordre_sids), 1)            # pas deux serpents
        self.assertFalse(p.peut_demarrer())

    def test_forfait(self):
        p = partie_prete()
        self.assertTrue(p.retirer_joueur("b"))
        self.assertEqual(p.statut, "terminee")
        self.assertEqual(p.vainqueur_sid, "a")
        self.assertEqual(p.scores_par_id(), {1: 0, 2: 0})  # score du partant gardé


if __name__ == "__main__":
    unittest.main()
