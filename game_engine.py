# -*- coding: utf-8 -*-
"""
game_engine.py — Moteur de jeu Serpentix (Snake + Slither 1v1)
-------------------------------------------------------------
Règles :
  - Deux serpents sur une grille
  - Manger une pomme → grandir (+1 segment) et +1 point
  - Toucher le corps de l'adversaire → mort (victoire adverse)
  - Toucher un mur → mort
  - Bonus « turbo » : vitesse +50 % pendant quelques ticks
  - Bonus « bouclier » : survit à un choc (corps ou mur)

Le serveur (Flask-SocketIO) appelle tick() régulièrement et diffuse l'état.
"""

import random
import string
from copy import deepcopy


# --- Constantes de jeu -------------------------------------------------------
LARGEUR = 40          # cases en largeur
HAUTEUR = 30          # cases en hauteur
TAILLE_DEPART = 3     # longueur initiale du serpent
NB_POMMES = 3         # pommes simultanées
NB_BONUS = 2          # bonus max sur le plateau
DUREE_TURBO = 40      # ticks de turbo (~4 s à 10 FPS)
MAX_JOUEURS = 2


def generer_code(longueur=6):
    """Génère un code de salle alphanumérique (ex. A3K9XZ)."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(longueur))


class Serpent:
    """Représente un serpent contrôlé par un joueur."""

    def __init__(self, joueur_id, pseudo, couleur, depart, direction):
        self.joueur_id = joueur_id
        self.pseudo = pseudo
        self.couleur = couleur
        # Corps : liste de (x, y), index 0 = tête
        self.corps = [depart]
        for i in range(1, TAILLE_DEPART):
            self.corps.append((depart[0] - direction[0] * i, depart[1] - direction[1] * i))
        self.direction = direction          # (dx, dy) actuelle
        self.prochaine_direction = direction
        self.score = 0
        self.vivant = True
        self.bouclier = False               # True = absorbe le prochain choc
        self.turbo_restant = 0              # ticks de turbo restants
        self.grandir = 0                    # segments à ajouter après un repas

    def changer_direction(self, dx, dy):
        """
        Change la direction demandée.
        Interdit de faire demi-tour (ex. droite → gauche).
        """
        # Demi-tour interdit
        if (dx, dy) == (-self.direction[0], -self.direction[1]):
            return
        if (dx, dy) in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            self.prochaine_direction = (dx, dy)

    def avancer(self):
        """Fait avancer la tête d'une case. Retourne la nouvelle position de tête."""
        self.direction = self.prochaine_direction
        tx, ty = self.corps[0]
        dx, dy = self.direction
        nouvelle_tete = (tx + dx, ty + dy)
        self.corps.insert(0, nouvelle_tete)
        if self.grandir > 0:
            self.grandir -= 1
        else:
            self.corps.pop()  # retire la queue
        if self.turbo_restant > 0:
            self.turbo_restant -= 1
        return nouvelle_tete

    def en_turbo(self):
        return self.turbo_restant > 0

    def to_dict(self):
        return {
            "joueur_id": self.joueur_id,
            "pseudo": self.pseudo,
            "couleur": self.couleur,
            "corps": self.corps,
            "score": self.score,
            "vivant": self.vivant,
            "bouclier": self.bouclier,
            "turbo": self.en_turbo(),
        }


class PartieEnCours:
    """État complet d'une partie 1v1 en mémoire (pas encore en BDD)."""

    def __init__(self, code, partie_db_id=None):
        self.code = code
        self.partie_db_id = partie_db_id
        self.joueurs = {}          # sid → Serpent
        self.ordre_sids = []       # ordre d'arrivée (max 2)
        self.pommes = []           # liste de (x, y)
        self.bonus = []            # liste de {"pos": (x,y), "type": "turbo"|"bouclier"}
        self.statut = "attente"    # attente | en_cours | terminee
        self.vainqueur_sid = None
        self.message_fin = ""
        self.ticks = 0

    def ajouter_joueur(self, sid, joueur_id, pseudo, couleur):
        """Ajoute un joueur s'il reste de la place. Retourne True/False."""
        if len(self.ordre_sids) >= MAX_JOUEURS:
            return False
        if sid in self.joueurs:
            return True

        # Positions de départ opposées
        if len(self.ordre_sids) == 0:
            depart, direction = (5, HAUTEUR // 2), (1, 0)
        else:
            depart, direction = (LARGEUR - 6, HAUTEUR // 2), (-1, 0)

        self.joueurs[sid] = Serpent(joueur_id, pseudo, couleur, depart, direction)
        self.ordre_sids.append(sid)
        return True

    def retirer_joueur(self, sid):
        """Retire un joueur (déconnexion). Si partie en cours → victoire adverse."""
        if sid not in self.joueurs:
            return
        if self.statut == "en_cours" and self.joueurs[sid].vivant:
            self.joueurs[sid].vivant = False
            # L'autre gagne par forfait
            for autre in self.ordre_sids:
                if autre != sid and self.joueurs[autre].vivant:
                    self.vainqueur_sid = autre
                    self.message_fin = f"{self.joueurs[autre].pseudo} gagne (adversaire déconnecté) !"
                    self.statut = "terminee"
        if sid in self.ordre_sids:
            self.ordre_sids.remove(sid)
        del self.joueurs[sid]

    def peut_demarrer(self):
        return len(self.ordre_sids) == MAX_JOUEURS and self.statut == "attente"

    def demarrer(self):
        """Lance la partie : place les pommes et les bonus."""
        self.statut = "en_cours"
        self._placer_pommes()
        self._placer_bonus()

    def _cases_occupees(self):
        """Ensemble de toutes les cases occupées (serpents + pommes + bonus)."""
        occ = set()
        for s in self.joueurs.values():
            occ.update(s.corps)
        occ.update(self.pommes)
        occ.update(b["pos"] for b in self.bonus)
        return occ

    def _case_libre(self):
        """Tire une case libre au hasard (ou None si plateau plein)."""
        occ = self._cases_occupees()
        libres = [
            (x, y)
            for x in range(LARGEUR)
            for y in range(HAUTEUR)
            if (x, y) not in occ
        ]
        return random.choice(libres) if libres else None

    def _placer_pommes(self):
        while len(self.pommes) < NB_POMMES:
            c = self._case_libre()
            if c is None:
                break
            self.pommes.append(c)

    def _placer_bonus(self):
        types = ["turbo", "bouclier"]
        while len(self.bonus) < NB_BONUS:
            c = self._case_libre()
            if c is None:
                break
            self.bonus.append({"pos": c, "type": random.choice(types)})

    def traiter_direction(self, sid, dx, dy):
        if sid in self.joueurs and self.joueurs[sid].vivant:
            self.joueurs[sid].changer_direction(dx, dy)

    def tick(self):
        """
        Un tour de jeu.
        Les serpents en turbo avancent 2 fois (vitesse doublée).
        Retourne True si l'état a changé de façon notable (fin de partie).
        """
        if self.statut != "en_cours":
            return False

        self.ticks += 1

        # 1) Avancer chaque serpent vivant (turbo = 2 pas)
        nouvelles_tetes = {}
        for sid, serpent in self.joueurs.items():
            if not serpent.vivant:
                continue
            pas = 2 if serpent.en_turbo() else 1
            for _ in range(pas):
                if not serpent.vivant:
                    break
                tete = serpent.avancer()
                nouvelles_tetes[sid] = tete

        # 2) Collisions murs / soi-même / adversaire
        for sid, serpent in list(self.joueurs.items()):
            if not serpent.vivant:
                continue
            tx, ty = serpent.corps[0]

            # Mur
            hors_limites = tx < 0 or ty < 0 or tx >= LARGEUR or ty >= HAUTEUR
            # Son propre corps (hors tête)
            collision_soi = (tx, ty) in serpent.corps[1:]
            # Corps de l'adversaire
            collision_adv = False
            for autre_sid, autre in self.joueurs.items():
                if autre_sid == sid:
                    continue
                if (tx, ty) in autre.corps:
                    collision_adv = True
                    break

            if hors_limites or collision_soi or collision_adv:
                if serpent.bouclier:
                    # Le bouclier absorbe un choc : on recule la tête
                    serpent.bouclier = False
                    serpent.corps.pop(0)
                    if not serpent.corps:
                        serpent.vivant = False
                    else:
                        # Remet une tête valide (ancienne 2e case)
                        pass
                else:
                    serpent.vivant = False

        # Collision tête contre tête → les deux meurent
        sids = [s for s in self.ordre_sids if s in self.joueurs]
        if len(sids) == 2:
            a, b = sids[0], sids[1]
            sa, sb = self.joueurs[a], self.joueurs[b]
            if sa.vivant and sb.vivant and sa.corps[0] == sb.corps[0]:
                if sa.bouclier:
                    sa.bouclier = False
                else:
                    sa.vivant = False
                if sb.bouclier:
                    sb.bouclier = False
                else:
                    sb.vivant = False

        # 3) Pommes
        for sid, serpent in self.joueurs.items():
            if not serpent.vivant:
                continue
            tete = serpent.corps[0]
            if tete in self.pommes:
                self.pommes.remove(tete)
                serpent.score += 1
                serpent.grandir += 1
        self._placer_pommes()

        # 4) Bonus
        for sid, serpent in self.joueurs.items():
            if not serpent.vivant:
                continue
            tete = serpent.corps[0]
            for b in list(self.bonus):
                if b["pos"] == tete:
                    self.bonus.remove(b)
                    if b["type"] == "turbo":
                        serpent.turbo_restant = DUREE_TURBO
                    elif b["type"] == "bouclier":
                        serpent.bouclier = True
        # Replacer un bonus de temps en temps
        if self.ticks % 50 == 0:
            self._placer_bonus()

        # 5) Fin de partie ?
        vivants = [s for s, ser in self.joueurs.items() if ser.vivant]
        if len(vivants) == 0:
            self.statut = "terminee"
            self.message_fin = "Match nul ! Les deux serpents sont hors jeu."
            self.vainqueur_sid = None
            return True
        if len(vivants) == 1 and len(self.joueurs) >= 2:
            self.statut = "terminee"
            self.vainqueur_sid = vivants[0]
            gagnant = self.joueurs[vivants[0]]
            self.message_fin = f"{gagnant.pseudo} remporte la partie !"
            return True

        return False

    def etat_public(self):
        """Dictionnaire sérialisable pour le client JavaScript."""
        return {
            "code": self.code,
            "statut": self.statut,
            "largeur": LARGEUR,
            "hauteur": HAUTEUR,
            "pommes": self.pommes,
            "bonus": self.bonus,
            "serpents": [s.to_dict() for s in self.joueurs.values()],
            "nb_joueurs": len(self.ordre_sids),
            "message_fin": self.message_fin,
            "vainqueur_id": (
                self.joueurs[self.vainqueur_sid].joueur_id
                if self.vainqueur_sid and self.vainqueur_sid in self.joueurs
                else None
            ),
        }

    def scores_par_id(self):
        """{utilisateur_id: score} pour la sauvegarde BDD."""
        return {s.joueur_id: s.score for s in self.joueurs.values()}
