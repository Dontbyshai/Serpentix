# Les bonus de Serpentix

Tous les réglages sont dans `game_engine.py` (dictionnaire `BONUS`). Les durées
sont écrites en secondes et converties en ticks avec `secondes()`, à partir de
la constante `TICKS_PAR_SECONDE` (7 pas par seconde).

Sur le plateau, chaque bonus est un **pictogramme blanc** dessiné en canvas
(`dessin.js`, fonction `pictogramme`) : pas d’emoji en couleur, le site reste
noir et blanc. Les effets actifs s’affichent sous le plateau avec un minuteur
et une barre qui se vide, et dans la pastille de chaque joueur.

| Bonus | Pictogramme | Effet | Durée | Fréquence (poids) | Solo |
|---|---|---|---|---|---|
| **Turbo** | triangle | Avance de 2 cases par tick (2 × la vitesse normale) | 3 s | 3 | oui |
| **Bouclier** | cercle avec un point | Annule UN choc mortel : le serpent recule d’une case et tourne vers une case libre | jusqu’au choc | 2 | oui |
| **Fantôme** | carré en pointillés | Traverse les corps (le sien et ceux des autres), et les autres le traversent. Les murs tuent toujours | 4 s | 2 | oui |
| **Aimant** | fer à cheval (U) | À chaque tick, les pommes à 6 cases ou moins se rapprochent d’une case de la tête | 6 s | 2 | oui |
| **Ciseaux** | croix à deux anneaux | Coupe la moitié du corps de l’ennemi le plus proche (il garde au moins 3 cases) ; les morceaux coupés deviennent des pommes | immédiat | 1 | non |
| **Gel** | flocon à 6 branches | Tous les adversaires n’avancent plus qu’un tick sur deux | 3 s | 1 | non |

## Équilibrage

- Le **poids** est la chance relative d’apparition : sur 11 bonus tirés, il y a
  en moyenne 3 turbos, 2 boucliers, 2 fantômes, 2 aimants, 1 ciseaux et 1 gel.
  Les deux bonus qui gênent directement l’adversaire (ciseaux, gel) sont les
  plus rares.
- Au plus **3 bonus** sur le plateau ; le serveur recomplète toutes les 5 s.
- Le fantôme ne protège pas des murs, et le turbo ne permet pas de « sauter »
  un corps : les collisions sont vérifiées après chaque case.
- Les ciseaux ne retirent pas de points (le score reste) : ils rendent la cible
  plus courte, donc perdante en cas de tête contre tête.
- En solo, ciseaux et gel n’apparaissent pas (pas d’adversaire).

## Où est le code

| Partie | Fichier | Fonction |
|---|---|---|
| Réglages | `game_engine.py` | `BONUS`, `RAYON_AIMANT`, `tirer_type_bonus()` |
| Effet au ramassage | `game_engine.py` | `PartieEnCours._activer_bonus()` |
| Aimant | `game_engine.py` | `PartieEnCours._attirer_pommes()` |
| Fantôme et gel | `game_engine.py` | `PartieEnCours._pas()` et `tick()` |
| Dessin | `static/js/dessin.js` | `pictogramme()`, `icone()`, `effetsHUD()` |
| Solo | `static/js/solo.js` | `unPas()`, `attirerPommes()` |
| Tests | `tests/test_game_engine.py` | classe `TestBonus` |
