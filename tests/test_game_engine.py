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

import game_engine as ge  # noqa: E402
from game_engine import PartieEnCours, Serpent, code_valide, positions_depart  # noqa: E402


def partie_prete(nb=2):
    """Crée une partie à nb joueurs (2 ou 3), démarrée, sans pommes ni bonus ni décompte."""
    p = PartieEnCours("TEST01", max_joueurs=nb)
    p.ajouter_joueur("a", 1, "Alice", "#ffffff")
    p.ajouter_joueur("b", 2, "Bob", "#ef4444")
    if nb == 3:
        p.ajouter_joueur("c", 3, "Chloé", "#22c55e")
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


def loin(p, sid, y):
    """Range le serpent sid sur une ligne lointaine (il avance vers la droite sans danger)."""
    placer(p, sid, [(5, y), (4, y), (3, y)], (1, 0))


class TestRegles(unittest.TestCase):
    """Règles de base (déjà valables en 1 contre 1)."""

    def test_vitesse_unique(self):
        # Toutes les durées découlent de TICKS_PAR_SECONDE
        self.assertEqual(ge.DECOMPTE_TICKS, 3 * ge.TICKS_PAR_SECONDE)
        self.assertEqual(ge.BONUS["turbo"]["duree"], 3 * ge.TICKS_PAR_SECONDE)
        self.assertLess(ge.TICKS_PAR_SECONDE, 10)       # plus lent qu'avant
        self.assertEqual(ge.PAS_TURBO, 2)               # turbo = 2 x la vitesse

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
        p.joueurs["a"].effets["turbo"] = 5
        p.tick()
        self.assertFalse(p.joueurs["a"].vivant)    # bloqué par le corps de b

    def test_turbo_avance_deux_fois_plus_vite(self):
        p = partie_prete()
        loin(p, "a", 5)
        loin(p, "b", 20)
        p.joueurs["a"].effets["turbo"] = 5
        p.tick()
        self.assertEqual(p.joueurs["a"].corps[0], (7, 5))   # 2 cases
        self.assertEqual(p.joueurs["b"].corps[0], (6, 20))  # 1 case

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


class TestTroisJoueurs(unittest.TestCase):
    """Parties à 3 : salle, départs équitables, collisions et vainqueur."""

    def test_salle_de_3_demarre_quand_pleine(self):
        p = PartieEnCours("TEST03", max_joueurs=3)
        p.ajouter_joueur("a", 1, "A", "#fff")
        p.ajouter_joueur("b", 2, "B", "#fff")
        self.assertFalse(p.peut_demarrer())               # 2/3 : on attend
        p.ajouter_joueur("c", 3, "C", "#fff")
        self.assertTrue(p.peut_demarrer())
        ok, msg = p.ajouter_joueur("d", 4, "D", "#fff")   # 4e joueur refusé
        self.assertFalse(ok)
        self.assertIn("3", msg)

    def test_max_joueurs_invalide(self):
        self.assertEqual(PartieEnCours("X", max_joueurs=9).max_joueurs, 2)

    def test_departs_equitables(self):
        places = positions_depart(3)
        cases = [c for c, _ in places]
        self.assertEqual(len(set(cases)), 3)              # trois cases différentes
        # Même distance jusqu'au mur d'en face pour chacun
        distances = []
        for (x, y), (dx, dy) in places:
            distances.append(y if dy == -1 else ge.HAUTEUR - 1 - y)
        self.assertEqual(len(set(distances)), 1)
        # Aucune collision pendant les 3 premières secondes si personne ne tourne
        p = PartieEnCours("TEST04", max_joueurs=3)
        for i, sid in enumerate("abc"):
            p.ajouter_joueur(sid, i + 1, sid, "#fff")
        p.demarrer()
        p.decompte = 0
        p.pommes, p.bonus = [], []
        p._placer_pommes = p._placer_bonus = lambda: None
        for _ in range(3 * ge.TICKS_PAR_SECONDE):
            self.assertFalse(p.tick())
        self.assertEqual(len(p._vivants()), 3)

    def test_places_donnees_au_demarrage(self):
        # a part de la salle d'attente, d arrive : pas deux serpents sur la même case
        p = PartieEnCours("TEST05", max_joueurs=3)
        for i, sid in enumerate("abc"):
            p.ajouter_joueur(sid, i + 1, sid, "#fff")
        p.retirer_joueur("a")
        p.ajouter_joueur("d", 4, "d", "#fff")
        p.demarrer()
        tetes = [p.joueurs[s].corps[0] for s in p.ordre_sids]
        self.assertEqual(len(set(tetes)), 3)

    def test_un_mort_la_partie_continue(self):
        p = partie_prete(3)
        placer(p, "a", [(39, 5), (38, 5), (37, 5)], (1, 0))   # va dans le mur
        loin(p, "b", 15)
        loin(p, "c", 25)
        self.assertFalse(p.tick())                 # il reste 2 serpents
        self.assertFalse(p.joueurs["a"].vivant)
        self.assertEqual(p.statut, "en_cours")
        self.assertTrue(p.pommes)                  # a lâché des pommes

    def test_dernier_vivant_gagne(self):
        p = partie_prete(3)
        p.joueurs["a"].vivant = False
        placer(p, "b", [(39, 5), (38, 5), (37, 5)], (1, 0))   # mur
        loin(p, "c", 25)
        self.assertTrue(p.tick())
        self.assertEqual(p.vainqueur_sid, "c")
        self.assertEqual(p.etat_public()["vainqueur_id"], 3)

    def test_tete_a_tete_a_trois_le_plus_long_survit(self):
        p = partie_prete(3)
        # Les 3 têtes arrivent sur la case (10, 10) au même tick
        placer(p, "a", [(9, 10), (8, 10), (7, 10), (6, 10)], (1, 0))    # 4 cases
        placer(p, "b", [(11, 10), (12, 10), (13, 10)], (-1, 0))         # 3 cases
        placer(p, "c", [(10, 11), (10, 12), (10, 13)], (0, -1))         # 3 cases
        self.assertTrue(p.tick())
        self.assertTrue(p.joueurs["a"].vivant)
        self.assertFalse(p.joueurs["b"].vivant)
        self.assertFalse(p.joueurs["c"].vivant)
        self.assertEqual(p.vainqueur_sid, "a")

    def test_tete_a_tete_a_deux_pendant_une_partie_a_trois(self):
        p = partie_prete(3)
        placer(p, "a", [(10, 10), (9, 10), (8, 10)], (1, 0))
        placer(p, "b", [(12, 10), (13, 10), (14, 10)], (-1, 0))         # égalité
        loin(p, "c", 25)
        self.assertTrue(p.tick())                  # a et b meurent : c gagne
        self.assertEqual(p.vainqueur_sid, "c")

    def test_match_nul_a_trois(self):
        p = partie_prete(3)
        p.joueurs["c"].vivant = False
        placer(p, "a", [(10, 10), (9, 10), (8, 10)], (1, 0))
        placer(p, "b", [(12, 10), (13, 10), (14, 10)], (-1, 0))
        self.assertTrue(p.tick())
        self.assertIsNone(p.vainqueur_sid)
        self.assertIn("nul", p.message_fin.lower())

    def test_depart_d_un_joueur_a_trois(self):
        p = partie_prete(3)
        self.assertFalse(p.retirer_joueur("a"))    # il reste b et c : on continue
        self.assertEqual(p.statut, "en_cours")
        self.assertTrue(p.retirer_joueur("b"))     # c reste seul : il gagne
        self.assertEqual(p.vainqueur_sid, "c")
        self.assertEqual(set(p.scores_par_id()), {1, 2, 3})  # 3 scores à enregistrer


class TestBonus(unittest.TestCase):
    """Les nouveaux bonus : fantôme, aimant, ciseaux, gel."""

    def test_fantome_traverse_un_corps(self):
        p = partie_prete()
        placer(p, "a", [(10, 10), (9, 10), (8, 10)], (1, 0))
        placer(p, "b", [(11, 12), (11, 11), (11, 10), (11, 9), (11, 8)], (0, 1))
        p.joueurs["a"].effets["fantome"] = 5
        p.tick()
        self.assertTrue(p.joueurs["a"].vivant)     # sans fantôme il mourrait
        self.assertTrue(p.joueurs["b"].vivant)

    def test_fantome_ne_traverse_pas_les_murs(self):
        p = partie_prete()
        placer(p, "a", [(39, 5), (38, 5), (37, 5)], (1, 0))
        loin(p, "b", 20)
        p.joueurs["a"].effets["fantome"] = 5
        p.tick()
        self.assertFalse(p.joueurs["a"].vivant)

    def test_aimant_attire_les_pommes(self):
        p = partie_prete()
        loin(p, "a", 5)                            # tête en (5,5) → (6,5)
        loin(p, "b", 20)
        p.pommes = [(6, 9), (30, 25)]
        p.joueurs["a"].effets["aimant"] = 10
        p.tick()
        self.assertEqual(p.pommes[0], (6, 8))      # s'est rapprochée d'une case
        self.assertEqual(p.pommes[1], (30, 25))    # trop loin : ne bouge pas

    def test_ciseaux_coupent_l_ennemi_le_plus_proche(self):
        p = partie_prete(3)
        loin(p, "a", 5)
        corps_b = [(15 - i, 8) for i in range(10)]        # 10 cases, proche de a
        placer(p, "b", corps_b, (1, 0))
        corps_c = [(15 - i, 25) for i in range(10)]       # 10 cases, loin de a
        placer(p, "c", corps_c, (1, 0))
        p.bonus = [{"pos": (6, 5), "type": "ciseaux"}]
        p.tick()
        self.assertEqual(len(p.joueurs["b"].corps), 5)    # coupé de moitié
        self.assertEqual(len(p.joueurs["c"].corps), 10)   # pas touché
        self.assertTrue(p.pommes)                         # morceaux → pommes

    def test_gel_ralentit_les_autres(self):
        p = partie_prete(3)
        loin(p, "a", 5)
        loin(p, "b", 15)
        loin(p, "c", 25)
        p.bonus = [{"pos": (6, 5), "type": "gel"}]
        for _ in range(4):
            p.tick()
        # a avance de 4 cases ; b et c, gelés, seulement d'environ la moitié
        self.assertEqual(p.joueurs["a"].corps[0], (9, 5))
        self.assertLess(p.joueurs["b"].corps[0][0], 9)
        self.assertLess(p.joueurs["c"].corps[0][0], 9)
        self.assertFalse(p.joueurs["a"].a_effet("gel"))   # pas soi-même

    def test_effets_dans_l_etat_public(self):
        p = partie_prete()
        p.joueurs["a"].effets["turbo"] = ge.TICKS_PAR_SECONDE * 2
        serpent = p.etat_public()["serpents"][0]
        self.assertEqual(serpent["effets"]["turbo"], 2.0)  # secondes restantes
        self.assertTrue(serpent["turbo"])

    def test_tous_les_types_existent(self):
        self.assertEqual(set(ge.BONUS),
                         {"turbo", "bouclier", "fantome", "aimant", "ciseaux", "gel"})
        for _ in range(50):
            self.assertIn(ge.tirer_type_bonus(), ge.BONUS)


if __name__ == "__main__":
    unittest.main()
