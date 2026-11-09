# -*- coding: utf-8 -*-
"""
game_engine.py — Moteur de jeu Serpentix (Snake + Slither, 1 contre 1)
=====================================================================

Ce module ne connaît NI Flask NI la base de données : il ne contient que les
règles du jeu. C'est un choix de décomposition (compétence NSI « décomposer un
problème en sous-problèmes ») : on peut tester les règles seules.

Règles du 1v1 :
  - deux serpents sur une grille de LARGEUR x HAUTEUR cases ;
  - manger une pomme  → +1 point et le serpent grandit d'une case ;
  - toucher un mur, son propre corps ou le CORPS adverse → éliminé ;
  - tête contre tête → le plus long gagne (égalité = les deux sont éliminés) ;
  - bonus « turbo »    : le serpent avance de 2 cases par tour pendant 3 s ;
  - bonus « bouclier » : annule UN choc mortel (le serpent recule et pivote).

Le serveur (app.py) appelle tick() 10 fois par seconde puis envoie
etat_public() aux deux navigateurs avec Socket.IO.
"""

import math
import random
import string


# --- Constantes de jeu -------------------------------------------------------
# Les mêmes valeurs sont recopiées dans static/js/solo.js pour le mode solo.
LARGEUR = 40            # nombre de cases en largeur
HAUTEUR = 30            # nombre de cases en hauteur
TAILLE_DEPART = 3       # longueur initiale d'un serpent
NB_POMMES = 3           # nombre de pommes présentes en même temps
NB_BONUS = 2            # nombre maximum de bonus sur le plateau
DUREE_TURBO = 30        # durée du turbo en ticks (30 ticks = 3 s à 10 ticks/s)
DECOMPTE_TICKS = 30     # compte à rebours avant le départ (3 s)
MAX_JOUEURS = 2         # c'est un duel
TAILLE_FILE = 2         # nb de virages mémorisés d'avance (touches rapides)
TICKS_PAR_SECONDE = 10  # doit correspondre à TICK_INTERVAL dans app.py

# Les 4 directions possibles sous forme de vecteurs (dx, dy).
# Attention : en informatique l'axe y descend (y = 0 est en haut).
DIRECTIONS = ((0, -1), (0, 1), (-1, 0), (1, 0))


def generer_code(longueur=6):
    """
    Génère un code de salle aléatoire.

    Paramètre : longueur (int) — nombre de caractères (6 par défaut).
    Retour    : str, par exemple "A3K9XZ" (lettres majuscules + chiffres).
    36^6 ≈ 2 milliards de codes possibles : impossible de deviner une salle.
    """
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(longueur))


def code_valide(code):
    """
    Vérifie le FORMAT d'un code de salle (6 caractères A-Z / 0-9).

    Paramètre : code (str ou autre)
    Retour    : bool
    Sert de validation côté serveur avant toute recherche (salle ou BDD).
    """
    return (
        isinstance(code, str)
        and len(code) == 6
        and all(c in string.ascii_uppercase + string.digits for c in code)
    )


class Serpent:
    """Un serpent contrôlé par un joueur (état en mémoire uniquement)."""

    def __init__(self, joueur_id, pseudo, couleur, depart, direction):
        """
        Paramètres :
          joueur_id (int) — id de l'utilisateur dans la table utilisateurs
          pseudo (str)    — nom affiché
          couleur (str)   — couleur hexadécimale du skin équipé
          depart (tuple)  — case (x, y) de la tête au départ
          direction (tuple) — vecteur (dx, dy) de départ
        """
        self.joueur_id = joueur_id
        self.pseudo = pseudo
        self.couleur = couleur
        # Corps = liste de cases (x, y). L'indice 0 est TOUJOURS la tête.
        # On construit le corps « derrière » la tête, à l'opposé de la direction.
        self.corps = [depart]
        for i in range(1, TAILLE_DEPART):
            self.corps.append((depart[0] - direction[0] * i,
                               depart[1] - direction[1] * i))
        self.direction = direction   # direction utilisée au dernier pas
        self.file_directions = []    # virages demandés pas encore appliqués
        self.score = 0               # pommes mangées
        self.vivant = True
        self.bouclier = False        # True = le prochain choc est annulé
        self.turbo_restant = 0       # ticks de turbo restants
        self.grandir = 0             # cases à ajouter (après un repas)
        self.sauvegarde = None       # copie avant le pas (pour le bouclier)

    def changer_direction(self, dx, dy):
        """
        Mémorise un virage demandé par le joueur.

        Paramètres : dx, dy (int) — vecteur parmi DIRECTIONS.
        Retour     : None.
        Pourquoi une FILE ? Si le joueur appuie très vite sur « haut » puis
        « gauche » entre deux ticks, on garde les deux virages au lieu de
        perdre le premier (sinon le jeu paraît « ne pas répondre »).
        """
        if (dx, dy) not in DIRECTIONS:
            return  # vecteur invalide envoyé par le client : on ignore
        # On compare au DERNIER virage prévu (ou à la direction actuelle)
        reference = self.file_directions[-1] if self.file_directions else self.direction
        if (dx, dy) == reference:
            return  # même direction : inutile
        if (dx, dy) == (-reference[0], -reference[1]):
            return  # demi-tour interdit (on se mangerait soi-même)
        if len(self.file_directions) < TAILLE_FILE:
            self.file_directions.append((dx, dy))

    def avancer(self):
        """
        Fait avancer le serpent d'UNE case.

        Retour : tuple (x, y) — la nouvelle position de la tête.
        Principe du Snake : on ajoute une tête devant et on retire la queue,
        sauf si le serpent doit grandir (alors la queue reste).
        """
        # Copie de l'état pour pouvoir annuler ce pas si le bouclier sert
        self.sauvegarde = (list(self.corps), self.grandir)
        if self.file_directions:
            self.direction = self.file_directions.pop(0)
        tx, ty = self.corps[0]
        dx, dy = self.direction
        nouvelle_tete = (tx + dx, ty + dy)
        self.corps.insert(0, nouvelle_tete)
        if self.grandir > 0:
            self.grandir -= 1
        else:
            self.corps.pop()  # retire la queue
        return nouvelle_tete

    def annuler_pas(self):
        """Remet le serpent à sa position d'avant le dernier pas (bouclier)."""
        if self.sauvegarde:
            self.corps, self.grandir = list(self.sauvegarde[0]), self.sauvegarde[1]
        self.file_directions = []

    def en_turbo(self):
        """Retour : bool — True si le turbo est actif."""
        return self.turbo_restant > 0

    def to_dict(self):
        """
        Convertit le serpent en dictionnaire « JSON-compatible ».
        Retour : dict envoyé au navigateur dans etat_jeu.
        """
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
    """
    État complet d'une partie 1v1, gardé en MÉMOIRE (pas en BDD) car il change
    10 fois par seconde. Seul le résultat final est écrit dans SQLite.
    """

    def __init__(self, code, partie_db_id=None):
        """
        Paramètres :
          code (str)          — code de salle à 6 caractères
          partie_db_id (int)  — id de la ligne correspondante dans la table parties
        """
        self.code = code
        self.partie_db_id = partie_db_id
        self.joueurs = {}          # sid Socket.IO → Serpent
        self.ordre_sids = []       # ordre d'arrivée (joueur 1, joueur 2)
        self.pommes = []           # liste de cases (x, y)
        self.bonus = []            # liste de {"pos": (x, y), "type": "turbo"|"bouclier"}
        self.statut = "attente"    # attente → en_cours → terminee
        self.vainqueur_sid = None
        self.message_fin = ""
        self.ticks = 0
        self.decompte = 0          # ticks restants avant le départ
        self.enregistree = False   # True une fois le résultat écrit en BDD

    # --- Gestion des joueurs ---------------------------------------------

    def ajouter_joueur(self, sid, joueur_id, pseudo, couleur):
        """
        Ajoute un joueur dans la salle.

        Paramètres : sid (identifiant de connexion Socket.IO), joueur_id,
                     pseudo, couleur.
        Retour     : (bool, str) — (succès, message d'erreur éventuel).
        """
        if sid in self.joueurs:
            return True, ""
        # Le même compte ne peut pas être deux fois dans la salle (sinon on
        # pourrait jouer contre soi-même dans deux onglets et gagner des coins).
        for ancien_sid, serpent in list(self.joueurs.items()):
            if serpent.joueur_id == joueur_id:
                if self.statut == "attente":
                    # Cas normal : la page a été rechargée → on remplace la connexion
                    self.joueurs[sid] = self.joueurs.pop(ancien_sid)
                    self.ordre_sids[self.ordre_sids.index(ancien_sid)] = sid
                    return True, ""
                return False, "Tu es déjà dans cette partie (autre onglet ?)."
        if self.statut != "attente":
            return False, "La partie a déjà commencé."
        if len(self.ordre_sids) >= MAX_JOUEURS:
            return False, "Salle pleine (2 joueurs max)."

        # Départs en diagonale : pas sur la même ligne, sinon les deux têtes
        # se rentrent dedans en 2 secondes si personne ne bouge.
        if len(self.ordre_sids) == 0:
            depart, direction = (5, HAUTEUR // 4), (1, 0)
        else:
            depart, direction = (LARGEUR - 6, HAUTEUR - 1 - HAUTEUR // 4), (-1, 0)

        self.joueurs[sid] = Serpent(joueur_id, pseudo, couleur, depart, direction)
        self.ordre_sids.append(sid)
        return True, ""

    def retirer_joueur(self, sid):
        """
        Gère le départ d'un joueur (onglet fermé, déconnexion…).

        Paramètre : sid.
        Retour    : bool — True si ce départ vient de TERMINER la partie
                    (l'adversaire gagne par forfait).
        Pendant une partie on garde le serpent (mort) pour enregistrer son
        score ; en salle d'attente on le supprime simplement.
        """
        if sid not in self.joueurs:
            return False
        if self.statut == "en_cours":
            self.joueurs[sid].vivant = False
            for autre in self.ordre_sids:
                if autre != sid and self.joueurs[autre].vivant:
                    self.vainqueur_sid = autre
                    self.message_fin = (
                        f"{self.joueurs[autre].pseudo} gagne : l'adversaire a quitté."
                    )
            if not self.vainqueur_sid:
                self.message_fin = "Partie abandonnée."
            self.statut = "terminee"
            return True
        if self.statut == "attente":
            self.ordre_sids.remove(sid)
            del self.joueurs[sid]
        return False

    def peut_demarrer(self):
        """Retour : bool — True si 2 joueurs sont là et que la partie attend."""
        return len(self.ordre_sids) == MAX_JOUEURS and self.statut == "attente"

    def demarrer(self):
        """Lance la partie : compte à rebours, pommes et bonus."""
        self.statut = "en_cours"
        self.decompte = DECOMPTE_TICKS
        self._placer_pommes()
        self._placer_bonus()

    # --- Placement des objets ---------------------------------------------

    def _cases_occupees(self):
        """Retour : set de toutes les cases prises (serpents, pommes, bonus)."""
        occ = set()
        for s in self.joueurs.values():
            occ.update(s.corps)
        occ.update(self.pommes)
        occ.update(b["pos"] for b in self.bonus)
        return occ

    def _case_libre(self):
        """Retour : une case (x, y) libre tirée au hasard, ou None si tout est plein."""
        occ = self._cases_occupees()
        libres = [(x, y) for x in range(LARGEUR) for y in range(HAUTEUR)
                  if (x, y) not in occ]
        return random.choice(libres) if libres else None

    def _placer_pommes(self):
        """Complète le plateau jusqu'à NB_POMMES pommes."""
        while len(self.pommes) < NB_POMMES:
            c = self._case_libre()
            if c is None:
                break
            self.pommes.append(c)

    def _placer_bonus(self):
        """Complète le plateau jusqu'à NB_BONUS bonus (type tiré au hasard)."""
        while len(self.bonus) < NB_BONUS:
            c = self._case_libre()
            if c is None:
                break
            self.bonus.append({"pos": c, "type": random.choice(["turbo", "bouclier"])})

    def traiter_direction(self, sid, dx, dy):
        """Transmet un virage au serpent du joueur sid (s'il est vivant)."""
        if sid in self.joueurs and self.joueurs[sid].vivant and self.decompte == 0:
            self.joueurs[sid].changer_direction(dx, dy)

    # --- Boucle de jeu --------------------------------------------------------

    def _hors_plateau(self, case):
        """Retour : bool — True si la case est en dehors de la grille (mur)."""
        x, y = case
        return x < 0 or y < 0 or x >= LARGEUR or y >= HAUTEUR

    def _pivoter(self, serpent):
        """
        Après un choc absorbé par le bouclier, tourne le serpent vers une case
        libre (à gauche ou à droite). Sinon il repartirait dans le même mur.
        """
        dx, dy = serpent.direction
        occupees = set()
        for s in self.joueurs.values():
            occupees.update(s.corps)
        for nd in ((dy, -dx), (-dy, dx)):  # les 2 directions perpendiculaires
            tx, ty = serpent.corps[0]
            case = (tx + nd[0], ty + nd[1])
            if not self._hors_plateau(case) and case not in occupees:
                serpent.direction = nd
                return

    def _pas(self, sids_qui_bougent):
        """
        Fait avancer d'UNE case les serpents donnés, puis gère collisions,
        pommes et bonus. Paramètre : liste de sid. Retour : None.
        On vérifie les collisions après CHAQUE case (même en turbo) pour qu'un
        serpent rapide ne puisse pas « sauter » par-dessus un corps.
        """
        anciennes_tetes = {}
        for sid in sids_qui_bougent:
            anciennes_tetes[sid] = self.joueurs[sid].corps[0]
            self.joueurs[sid].avancer()

        # Deux ensembles séparés : chocs « simples » (mur / soi-même) et chocs
        # contre l'adversaire (qui peuvent être annulés par la règle tête-à-tête).
        choc_simple, choc_adverse = set(), set()
        for sid in sids_qui_bougent:
            s = self.joueurs[sid]
            tete = s.corps[0]
            if self._hors_plateau(tete) or tete in s.corps[1:]:
                choc_simple.add(sid)
            for autre_sid, autre in self.joueurs.items():
                if autre_sid != sid and autre.vivant and tete in autre.corps[1:]:
                    choc_adverse.add(sid)  # tête dans le CORPS adverse

        # Tête contre tête : même case, ou les deux têtes se croisent
        vivants = [s for s in self.ordre_sids if self.joueurs[s].vivant]
        if len(vivants) == 2:
            a, b = vivants
            sa, sb = self.joueurs[a], self.joueurs[b]
            croisement = (a in anciennes_tetes and b in anciennes_tetes
                          and sa.corps[0] == anciennes_tetes[b]
                          and sb.corps[0] == anciennes_tetes[a])
            if sa.corps[0] == sb.corps[0] or croisement:
                # Règle « Slither » : le plus long l'emporte, égalité = les deux
                choc_adverse.discard(a)
                choc_adverse.discard(b)
                if len(sa.corps) >= len(sb.corps):
                    choc_adverse.add(b)
                if len(sb.corps) >= len(sa.corps):
                    choc_adverse.add(a)

        en_danger = choc_simple | choc_adverse
        for sid in en_danger:
            s = self.joueurs[sid]
            if s.bouclier:
                s.bouclier = False   # le bouclier est consommé
                s.annuler_pas()      # on revient sur la case d'avant
                self._pivoter(s)     # et on tourne vers une case libre
            else:
                s.vivant = False

        # Pommes et bonus : seulement pour ceux qui ont vraiment avancé
        for sid in sids_qui_bougent:
            s = self.joueurs[sid]
            if not s.vivant or sid in en_danger:
                continue
            tete = s.corps[0]
            if tete in self.pommes:
                self.pommes.remove(tete)
                s.score += 1
                s.grandir += 1
            for b in list(self.bonus):
                if b["pos"] == tete:
                    self.bonus.remove(b)
                    if b["type"] == "turbo":
                        s.turbo_restant = DUREE_TURBO
                    else:
                        s.bouclier = True

    def tick(self):
        """
        Un tour de jeu (appelé 10 fois par seconde par app.py).

        Retour : bool — True si la partie VIENT de se terminer (il faut alors
                 enregistrer le résultat en base).
        """
        if self.statut != "en_cours":
            return False
        if self.decompte > 0:          # 3, 2, 1… les serpents ne bougent pas
            self.decompte -= 1
            return False

        self.ticks += 1
        # 1er pas : tout le monde avance ; 2e pas : seulement ceux en turbo
        for numero_pas in range(2):
            qui = [sid for sid in self.ordre_sids
                   if self.joueurs[sid].vivant
                   and (numero_pas == 0 or self.joueurs[sid].en_turbo())]
            if qui:
                self._pas(qui)
        for s in self.joueurs.values():
            if s.turbo_restant > 0:
                s.turbo_restant -= 1

        self._placer_pommes()
        if self.ticks % 50 == 0:   # toutes les 5 s, on recomplète les bonus
            self._placer_bonus()

        # Fin de partie ?
        vivants = [sid for sid in self.ordre_sids if self.joueurs[sid].vivant]
        if len(vivants) == 0:
            self.statut = "terminee"
            self.message_fin = "Match nul ! Les deux serpents sont éliminés."
            return True
        if len(vivants) == 1:
            self.statut = "terminee"
            self.vainqueur_sid = vivants[0]
            self.message_fin = f"{self.joueurs[vivants[0]].pseudo} remporte la partie !"
            return True
        return False

    def etat_public(self):
        """
        Retour : dict sérialisable en JSON, envoyé aux navigateurs (événement
        etat_jeu). Le client ne fait que DESSINER cet état : c'est le serveur
        qui décide de tout (le client ne peut donc pas tricher sur les règles).
        """
        return {
            "code": self.code,
            "statut": self.statut,
            "largeur": LARGEUR,
            "hauteur": HAUTEUR,
            "pommes": self.pommes,
            "bonus": self.bonus,
            "serpents": [self.joueurs[sid].to_dict() for sid in self.ordre_sids],
            "nb_joueurs": len(self.ordre_sids),
            # Secondes restantes du compte à rebours (arrondi au-dessus)
            "decompte": math.ceil(self.decompte / TICKS_PAR_SECONDE),
            "message_fin": self.message_fin,
            "vainqueur_id": (
                self.joueurs[self.vainqueur_sid].joueur_id
                if self.vainqueur_sid in self.joueurs else None
            ),
        }

    def scores_par_id(self):
        """Retour : dict {utilisateur_id: score} pour la sauvegarde en BDD."""
        return {s.joueur_id: s.score for s in self.joueurs.values()}
