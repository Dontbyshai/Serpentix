# -*- coding: utf-8 -*-
"""
game_engine.py — Moteur de jeu Serpentix (Snake + Slither, 2 ou 3 joueurs)
==========================================================================

Ce module ne connaît NI Flask NI la base de données : il ne contient que les
règles du jeu. C'est un choix de décomposition (compétence NSI « décomposer un
problème en sous-problèmes ») : on peut tester les règles seules
(voir tests/test_game_engine.py).

Règles d'une partie (2 ou 3 serpents) :
  - plateau de LARGEUR x HAUTEUR cases ;
  - manger une pomme → +1 point et le serpent grandit d'une case ;
  - toucher un mur, son propre corps ou le CORPS d'un adversaire → éliminé ;
  - tête contre tête → le plus long survit, à égalité les deux sont éliminés ;
  - un serpent éliminé lâche des pommes là où était son corps (comme Slither) ;
  - le DERNIER serpent en vie gagne ; si les derniers meurent en même temps,
    c'est un match nul.

Les 6 bonus (voir BONUS plus bas et docs/bonus.md) :
  turbo, bouclier, fantôme, aimant, ciseaux, gel.

Le serveur (app.py) appelle tick() TICKS_PAR_SECONDE fois par seconde puis
envoie etat_public() à tous les navigateurs de la salle avec Socket.IO.
"""

import math
import random
import string


# --- Vitesse du jeu ----------------------------------------------------------
# LA constante qui règle la vitesse : nombre de pas par seconde.
# Avant : 10 (trop rapide). Maintenant : 7 → le jeu est 30 % plus lent.
# Tout le reste (turbo, durées des bonus, compte à rebours, mode solo) est
# calculé à partir d'elle : il suffit de changer ce nombre pour tout ralentir
# ou tout accélérer.
TICKS_PAR_SECONDE = 7


def secondes(s):
    """
    Convertit une durée en secondes en nombre de ticks.
    Paramètre : s (float). Retour : int (au moins 1).
    Exemple : secondes(3) = 21 ticks quand TICKS_PAR_SECONDE = 7.
    """
    return max(1, round(s * TICKS_PAR_SECONDE))


# --- Constantes de jeu -------------------------------------------------------
LARGEUR = 40            # nombre de cases en largeur
HAUTEUR = 30            # nombre de cases en hauteur
TAILLE_DEPART = 3       # longueur initiale d'un serpent
NB_POMMES = 4           # nombre de pommes présentes en même temps
NB_BONUS = 3            # nombre maximum de bonus sur le plateau
JOUEURS_POSSIBLES = (2, 3)   # le créateur choisit une salle de 2 ou de 3
TAILLE_FILE = 2         # nb de virages mémorisés d'avance (touches rapides)
PAS_TURBO = 2           # en turbo on avance de 2 cases par tick (2 x la vitesse normale)
DECOMPTE_TICKS = secondes(3)       # compte à rebours avant le départ
RECHARGE_BONUS = secondes(5)       # toutes les 5 s on recomplète les bonus
POMMES_LACHEES_MAX = 10            # pommes max lâchées par un serpent éliminé

# --- Bonus ---------------------------------------------------------------------
# Pour chaque type : durée de l'effet (en ticks, 0 = effet immédiat) et
# « poids » du tirage au sort (2 = deux fois plus fréquent que 1).
BONUS = {
    "turbo":    {"duree": secondes(3), "poids": 3},  # avance 2 fois plus vite
    "bouclier": {"duree": 0,           "poids": 2},  # annule UN choc mortel
    "fantome":  {"duree": secondes(4), "poids": 2},  # traverse les corps
    "aimant":   {"duree": secondes(6), "poids": 2},  # attire les pommes proches
    "ciseaux":  {"duree": 0,           "poids": 1},  # coupe la queue de l'ennemi le plus proche
    "gel":      {"duree": secondes(3), "poids": 1},  # ralentit tous les autres serpents
}
# Effets qui ont un minuteur (affichés dans le HUD avec le temps restant)
EFFETS_MINUTES = ("turbo", "fantome", "aimant", "gel")
RAYON_AIMANT = 6        # distance (en cases) à laquelle l'aimant attire les pommes

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


def positions_depart(nb_joueurs):
    """
    Cases de départ ÉQUITABLES selon le nombre de joueurs.

    Paramètre : nb_joueurs (2 ou 3).
    Retour    : liste de (case_tete, direction).
    - À 2 : départs en diagonale qui ne se croisent pas tout de suite.
    - À 3 : trois colonnes espacées de 10 cases ; on alterne montée / descente.
      Chaque serpent a exactement la même distance jusqu'au mur d'en face
      (HAUTEUR - 5 cases) et les trajectoires sont parallèles : personne
      n'est avantagé au départ.
    """
    if nb_joueurs == 3:
        return [
            ((LARGEUR // 4, HAUTEUR - 5), (0, -1)),          # gauche, monte
            ((LARGEUR // 2, 4), (0, 1)),                     # centre, descend
            ((3 * LARGEUR // 4, HAUTEUR - 5), (0, -1)),      # droite, monte
        ]
    return [
        ((5, HAUTEUR // 4), (1, 0)),
        ((LARGEUR - 6, HAUTEUR - 1 - HAUTEUR // 4), (-1, 0)),
    ]


def tirer_type_bonus(types=None):
    """
    Tire un type de bonus au hasard en tenant compte des poids.
    Paramètre : types (liste de noms autorisés, tous par défaut).
    Retour    : str (clé de BONUS).
    """
    types = list(types or BONUS.keys())
    poids = [BONUS[t]["poids"] for t in types]
    return random.choices(types, weights=poids, k=1)[0]


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
        self.score = 0               # pommes mangées
        self.vivant = True
        self.bouclier = False        # True = le prochain choc est annulé
        # Minuteurs des effets en cours (en ticks restants, 0 = inactif)
        self.effets = {nom: 0 for nom in EFFETS_MINUTES}
        self.grandir = 0             # cases à ajouter (après un repas)
        self.sauvegarde = None       # copie avant le pas (pour le bouclier)
        self.reinitialiser(depart, direction)

    def reinitialiser(self, depart, direction):
        """
        (Re)place le serpent sur sa case de départ.
        Corps = liste de cases (x, y). L'indice 0 est TOUJOURS la tête ;
        on construit le corps « derrière » la tête, à l'opposé de la direction.
        """
        self.corps = [depart]
        for i in range(1, TAILLE_DEPART):
            self.corps.append((depart[0] - direction[0] * i,
                               depart[1] - direction[1] * i))
        self.direction = direction   # direction utilisée au dernier pas
        self.file_directions = []    # virages demandés pas encore appliqués

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

    def a_effet(self, nom):
        """Retour : bool — True si l'effet minuté « nom » est actif."""
        return self.effets.get(nom, 0) > 0

    def en_turbo(self):
        """Retour : bool — True si le turbo est actif."""
        return self.a_effet("turbo")

    def to_dict(self):
        """
        Convertit le serpent en dictionnaire « JSON-compatible ».
        Retour : dict envoyé au navigateur dans etat_jeu.
        « effets » donne, pour chaque effet actif, les SECONDES restantes
        (le HUD affiche un minuteur).
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
            "fantome": self.a_effet("fantome"),
            "gele": self.a_effet("gel"),
            "effets": {
                nom: round(t / TICKS_PAR_SECONDE, 1)
                for nom, t in self.effets.items() if t > 0
            },
        }


class PartieEnCours:
    """
    État complet d'une partie (2 ou 3 joueurs), gardé en MÉMOIRE (pas en BDD)
    car il change plusieurs fois par seconde. Seul le résultat final est écrit
    dans SQLite.
    """

    def __init__(self, code, partie_db_id=None, max_joueurs=2):
        """
        Paramètres :
          code (str)          — code de salle à 6 caractères
          partie_db_id (int)  — id de la ligne correspondante dans la table parties
          max_joueurs (int)   — 2 ou 3 : la partie démarre quand la salle est pleine
        """
        if max_joueurs not in JOUEURS_POSSIBLES:
            max_joueurs = 2  # valeur inattendue : on revient au duel
        self.code = code
        self.partie_db_id = partie_db_id
        self.max_joueurs = max_joueurs
        self.joueurs = {}          # sid Socket.IO → Serpent
        self.ordre_sids = []       # ordre d'arrivée (joueur 1, 2, 3)
        self.pommes = []           # liste de cases (x, y)
        self.bonus = []            # liste de {"pos": (x, y), "type": str}
        self.statut = "attente"    # attente → en_cours → terminee
        self.vainqueur_sid = None
        self.message_fin = ""
        self.ticks = 0
        self.decompte = 0          # ticks restants avant le départ
        self.enregistree = False   # True une fois le résultat écrit en BDD
        self.evenements = []       # petits messages du tick (« X a coupé Y »)

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
        if len(self.ordre_sids) >= self.max_joueurs:
            return False, f"Salle pleine ({self.max_joueurs} joueurs max)."

        # Position provisoire : les vraies places sont données au démarrage
        # (voir _placer_serpents), quand on sait QUI est là.
        depart, direction = positions_depart(self.max_joueurs)[len(self.ordre_sids)]
        self.joueurs[sid] = Serpent(joueur_id, pseudo, couleur, depart, direction)
        self.ordre_sids.append(sid)
        return True, ""

    def retirer_joueur(self, sid):
        """
        Gère le départ d'un joueur (onglet fermé, déconnexion…).

        Paramètre : sid.
        Retour    : bool — True si ce départ vient de TERMINER la partie.
        Pendant une partie, le serpent du partant est éliminé (on le garde
        pour enregistrer son score). À 3, la partie continue tant qu'il reste
        au moins 2 serpents ; sinon le dernier gagne par forfait.
        En salle d'attente, on retire simplement le joueur.
        """
        if sid not in self.joueurs:
            return False
        if self.statut == "en_cours":
            self.joueurs[sid].vivant = False
            vivants = [s for s in self.ordre_sids if self.joueurs[s].vivant]
            if len(vivants) >= 2:
                self.evenements.append(f"{self.joueurs[sid].pseudo} a quitté la partie.")
                return False
            if vivants:
                self.vainqueur_sid = vivants[0]
                self.message_fin = (
                    f"{self.joueurs[vivants[0]].pseudo} gagne : les autres ont quitté."
                )
            else:
                self.message_fin = "Partie abandonnée."
            self.statut = "terminee"
            return True
        if self.statut == "attente":
            self.ordre_sids.remove(sid)
            del self.joueurs[sid]
        return False

    def peut_demarrer(self):
        """Retour : bool — True si la salle est pleine et que la partie attend."""
        return len(self.ordre_sids) == self.max_joueurs and self.statut == "attente"

    def demarrer(self):
        """Lance la partie : places de départ, compte à rebours, pommes et bonus."""
        self.statut = "en_cours"
        self.decompte = DECOMPTE_TICKS
        self._placer_serpents()
        self._placer_pommes()
        self._placer_bonus()

    def _placer_serpents(self):
        """
        Donne à chaque joueur sa case de départ selon l'ordre d'arrivée.
        Fait au DÉMARRAGE (et pas à l'arrivée) : si quelqu'un quitte la salle
        d'attente puis qu'un autre arrive, deux serpents ne peuvent pas se
        retrouver sur la même case.
        """
        places = positions_depart(self.max_joueurs)
        for i, sid in enumerate(self.ordre_sids):
            depart, direction = places[i]
            self.joueurs[sid].reinitialiser(depart, direction)

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
        """Complète le plateau jusqu'à NB_BONUS bonus (type tiré au hasard, pondéré)."""
        while len(self.bonus) < NB_BONUS:
            c = self._case_libre()
            if c is None:
                break
            self.bonus.append({"pos": c, "type": tirer_type_bonus()})

    def traiter_direction(self, sid, dx, dy):
        """Transmet un virage au serpent du joueur sid (s'il est vivant)."""
        if sid in self.joueurs and self.joueurs[sid].vivant and self.decompte == 0:
            self.joueurs[sid].changer_direction(dx, dy)

    # --- Outils pour les règles ---------------------------------------------

    def _hors_plateau(self, case):
        """Retour : bool — True si la case est en dehors de la grille (mur)."""
        x, y = case
        return x < 0 or y < 0 or x >= LARGEUR or y >= HAUTEUR

    def _vivants(self):
        """Retour : liste des sid des serpents encore en vie (ordre d'arrivée)."""
        return [sid for sid in self.ordre_sids if self.joueurs[sid].vivant]

    def _pivoter(self, serpent):
        """
        Après un choc absorbé par le bouclier, tourne le serpent vers une case
        libre (à gauche ou à droite). Sinon il repartirait dans le même mur.
        """
        dx, dy = serpent.direction
        occupees = set()
        for s in self.joueurs.values():
            if s.vivant:
                occupees.update(s.corps)
        for nd in ((dy, -dx), (-dy, dx)):  # les 2 directions perpendiculaires
            tx, ty = serpent.corps[0]
            case = (tx + nd[0], ty + nd[1])
            if not self._hors_plateau(case) and case not in occupees:
                serpent.direction = nd
                return

    def _lacher_pommes(self, serpent):
        """
        Règle « Slither » : un serpent éliminé laisse des pommes là où était
        son corps (une case sur deux, au plus POMMES_LACHEES_MAX).
        """
        lachees = 0
        for case in serpent.corps[1::2]:
            if lachees >= POMMES_LACHEES_MAX:
                break
            if not self._hors_plateau(case) and case not in self.pommes:
                self.pommes.append(case)
                lachees += 1

    def _ennemi_le_plus_proche(self, sid):
        """
        Retour : sid du serpent ennemi vivant dont la tête est la plus proche
        (distance de Manhattan |dx| + |dy|), ou None.
        """
        tete = self.joueurs[sid].corps[0]
        meilleur, distance_min = None, None
        for autre in self._vivants():
            if autre == sid:
                continue
            ax, ay = self.joueurs[autre].corps[0]
            d = abs(ax - tete[0]) + abs(ay - tete[1])
            if distance_min is None or d < distance_min:
                meilleur, distance_min = autre, d
        return meilleur

    def _activer_bonus(self, sid, type_bonus):
        """
        Applique l'effet d'un bonus ramassé par le serpent sid.
        Paramètres : sid (str), type_bonus (clé de BONUS).
        """
        s = self.joueurs[sid]
        if type_bonus == "bouclier":
            s.bouclier = True
        elif type_bonus == "ciseaux":
            cible = self._ennemi_le_plus_proche(sid)
            if cible:
                c = self.joueurs[cible]
                # On coupe la MOITIÉ du corps (mais il garde au moins TAILLE_DEPART cases)
                garder = max(TAILLE_DEPART, len(c.corps) // 2)
                coupe = c.corps[garder:]
                c.corps = c.corps[:garder]
                c.grandir = 0
                # Les morceaux coupés deviennent des pommes (une case sur deux)
                for case in coupe[::2][:POMMES_LACHEES_MAX]:
                    if case not in self.pommes:
                        self.pommes.append(case)
                self.evenements.append(f"{s.pseudo} coupe la queue de {c.pseudo} !")
        elif type_bonus == "gel":
            # Le gel touche TOUS les autres serpents vivants
            for autre in self._vivants():
                if autre != sid:
                    self.joueurs[autre].effets["gel"] = BONUS["gel"]["duree"]
            self.evenements.append(f"{s.pseudo} gèle ses adversaires !")
        else:
            # turbo, fantome, aimant : effet minuté sur le serpent lui-même
            s.effets[type_bonus] = BONUS[type_bonus]["duree"]

    def _attirer_pommes(self):
        """
        Effet « aimant » : chaque pomme à moins de RAYON_AIMANT cases de la tête
        d'un serpent aimanté se rapproche d'une case vers cette tête (sur l'axe
        où l'écart est le plus grand), si la case visée est libre.
        """
        corps = set()
        for s in self.joueurs.values():
            if s.vivant:
                corps.update(s.corps)
        for sid in self._vivants():
            s = self.joueurs[sid]
            if not s.a_effet("aimant"):
                continue
            hx, hy = s.corps[0]
            for i, (px, py) in enumerate(self.pommes):
                ecart_x, ecart_y = hx - px, hy - py
                if abs(ecart_x) + abs(ecart_y) > RAYON_AIMANT:
                    continue
                if abs(ecart_x) >= abs(ecart_y):
                    case = (px + (1 if ecart_x > 0 else -1), py)
                else:
                    case = (px, py + (1 if ecart_y > 0 else -1))
                # On ne pose jamais une pomme SUR un corps (elle serait perdue)
                if case not in corps and case not in self.pommes:
                    self.pommes[i] = case

    # --- Boucle de jeu --------------------------------------------------------

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

        vivants = self._vivants()   # liste figée AVANT les éliminations de ce pas

        def se_croisent(a, b):
            """Vrai si les têtes de a et b ont échangé leurs cases (passage l'une dans l'autre)."""
            return (a in anciennes_tetes and b in anciennes_tetes
                    and self.joueurs[a].corps[0] == anciennes_tetes[b]
                    and self.joueurs[b].corps[0] == anciennes_tetes[a])

        en_danger = set()
        # 1) Murs, son propre corps et corps des adversaires
        for sid in sids_qui_bougent:
            s = self.joueurs[sid]
            tete = s.corps[0]
            if self._hors_plateau(tete):
                en_danger.add(sid)          # le fantôme ne traverse PAS les murs
                continue
            if not s.a_effet("fantome") and tete in s.corps[1:]:
                en_danger.add(sid)          # il se mord la queue
            for autre_sid in vivants:
                autre = self.joueurs[autre_sid]
                if autre_sid == sid:
                    continue
                if s.a_effet("fantome") or autre.a_effet("fantome"):
                    continue                # un fantôme ne touche personne
                if tete in autre.corps[1:] and not se_croisent(sid, autre_sid):
                    en_danger.add(sid)      # tête dans le CORPS d'un adversaire

        # 2) Tête contre tête, pour CHAQUE paire de serpents (fonctionne à 2 ou 3).
        #    Règle Slither : le plus long survit, à égalité les deux sont éliminés.
        #    À 3 dans la même case : seul le plus long (s'il est unique) survit.
        for i, a in enumerate(vivants):
            for b in vivants[i + 1:]:
                sa, sb = self.joueurs[a], self.joueurs[b]
                if sa.a_effet("fantome") or sb.a_effet("fantome"):
                    continue
                if sa.corps[0] == sb.corps[0] or se_croisent(a, b):
                    if len(sa.corps) >= len(sb.corps):
                        en_danger.add(b)
                    if len(sb.corps) >= len(sa.corps):
                        en_danger.add(a)

        # 3) Bouclier ou élimination
        for sid in en_danger:
            s = self.joueurs[sid]
            if s.bouclier:
                s.bouclier = False   # le bouclier est consommé
                s.annuler_pas()      # on revient sur la case d'avant
                self._pivoter(s)     # et on tourne vers une case libre
            else:
                s.vivant = False

        # 4) Pommes et bonus : seulement pour ceux qui ont vraiment avancé
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
                    self._activer_bonus(sid, b["type"])

        # 5) Les serpents éliminés lâchent leurs pommes (si la partie continue)
        morts = [sid for sid in en_danger if not self.joueurs[sid].vivant]
        if morts and len(self._vivants()) >= 2:
            for sid in morts:
                self._lacher_pommes(self.joueurs[sid])
                self.evenements.append(f"{self.joueurs[sid].pseudo} est éliminé.")

    def tick(self):
        """
        Un tour de jeu (appelé TICKS_PAR_SECONDE fois par seconde par app.py).

        Retour : bool — True si la partie VIENT de se terminer (il faut alors
                 enregistrer le résultat en base).
        """
        if self.statut != "en_cours":
            return False
        if self.decompte > 0:          # 3, 2, 1… les serpents ne bougent pas
            self.decompte -= 1
            return False

        self.ticks += 1
        self.evenements = []
        # Pas n°0 : tout le monde avance (sauf les serpents gelés, qui
        # n'avancent qu'un tick sur deux). Pas n°1 : seulement ceux en turbo.
        for numero_pas in range(PAS_TURBO):
            qui = []
            for sid in self._vivants():
                s = self.joueurs[sid]
                if s.a_effet("gel") and self.ticks % 2 == 1:
                    continue           # gelé : il saute ce tick
                if numero_pas == 0 or s.en_turbo():
                    qui.append(sid)
            if qui:
                self._pas(qui)

        self._attirer_pommes()
        # Les minuteurs des effets diminuent d'un tick
        for s in self.joueurs.values():
            for nom in s.effets:
                if s.effets[nom] > 0:
                    s.effets[nom] -= 1

        self._placer_pommes()
        if self.ticks % RECHARGE_BONUS == 0:
            self._placer_bonus()

        # Fin de partie ? Il faut qu'il reste AU PLUS un serpent.
        vivants = self._vivants()
        if len(vivants) == 0:
            self.statut = "terminee"
            self.message_fin = "Match nul ! Les derniers serpents sont éliminés en même temps."
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
        vainqueur = self.joueurs.get(self.vainqueur_sid)
        return {
            "code": self.code,
            "statut": self.statut,
            "largeur": LARGEUR,
            "hauteur": HAUTEUR,
            "pommes": self.pommes,
            "bonus": self.bonus,
            "serpents": [self.joueurs[sid].to_dict() for sid in self.ordre_sids],
            "nb_joueurs": len(self.ordre_sids),
            "max_joueurs": self.max_joueurs,
            # Secondes restantes du compte à rebours (arrondi au-dessus)
            "decompte": math.ceil(self.decompte / TICKS_PAR_SECONDE),
            "message_fin": self.message_fin,
            "evenements": self.evenements,
            "vainqueur_id": vainqueur.joueur_id if vainqueur else None,
            "vainqueur_couleur": vainqueur.couleur if vainqueur else None,
        }

    def scores_par_id(self):
        """Retour : dict {utilisateur_id: score} pour la sauvegarde en BDD."""
        return {s.joueur_id: s.score for s in self.joueurs.values()}


def reglages_client():
    """
    Retour : dict des réglages utiles au mode solo (solo.js).
    Le template solo.html les injecte dans la page : le solo utilise donc
    EXACTEMENT les mêmes valeurs que le serveur (une seule source de vérité).
    """
    return {
        "ticks_par_seconde": TICKS_PAR_SECONDE,
        "largeur": LARGEUR,
        "hauteur": HAUTEUR,
        "taille_depart": TAILLE_DEPART,
        "nb_pommes": NB_POMMES,
        "nb_bonus": NB_BONUS,
        "pas_turbo": PAS_TURBO,
        "decompte": DECOMPTE_TICKS,
        "recharge_bonus": RECHARGE_BONUS,
        "rayon_aimant": RAYON_AIMANT,
        # En solo il n'y a pas d'adversaire : ciseaux et gel n'existent pas
        "bonus": {nom: BONUS[nom] for nom in ("turbo", "bouclier", "fantome", "aimant")},
    }
