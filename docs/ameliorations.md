# Améliorations possibles

Liste classée par priorité. Chaque idée reste dans le cadre du programme de NSI.

## Déjà réalisé (version 6)

- Jeu ralenti : 7 pas par seconde au lieu de 10, réglé par une seule constante
  (`TICKS_PAR_SECONDE`).
- Parties à **2 ou 3 joueurs** (colonne `parties.nb_joueurs`), départs
  équitables, dernier survivant gagnant.
- **4 nouveaux bonus** : fantôme, aimant, ciseaux, gel ([bonus.md](bonus.md)),
  effets affichés avec un minuteur.
- Écrans de fin animés (victoire, défaite, match nul).
- Classement avec podium, tri, victoires / nuls / défaites / % de victoires et
  meilleur score.
- Arène animée derrière l’accueil ; page bloquée (aucun défilement) pendant le jeu.

## Idées restantes

## Priorité 1 : utile et faisable rapidement

1. **Bouton « Revanche »** à la fin d’une partie : recrée une salle avec les
   mêmes joueurs. *NSI : réutiliser les fonctions existantes (`creer_partie`,
   `ajouter_participant`), nouvel événement Socket.IO.*
2. **Table `parties_solo`** (id, utilisateur_id, score, durée, date) pour garder
   le meilleur score solo et l’afficher dans le profil et le classement.
   *NSI : nouvelle table, clé étrangère, `INSERT` puis `SELECT MAX(score)`.*
3. **Limiter les essais de connexion** (ex. 5 échecs = attendre 1 minute).
   *NSI : sécurité côté serveur avec un dictionnaire ou une table.*
4. **Formulaire de recherche / tri** dans la gestion des joueurs (par pseudo,
   par coins). *NSI : `WHERE pseudo LIKE ?` et `ORDER BY` choisi parmi une liste
   autorisée.*

## Priorité 2 : enrichir le jeu

5. **File d’attente automatique** (« Partie rapide ») : le serveur regroupe
   2 ou 3 joueurs qui attendent. *NSI : structure de données file (FIFO).*
6. **Mode spectateur** : rejoindre une salle pleine en lecture seule.
   *NSI : rooms Socket.IO, droits différents selon le rôle.*
7. **Plateau qui rétrécit** après 2 minutes pour éviter les parties trop
   longues. *NSI : paramètres de l’algorithme.*
7 bis. **Classement de la partie à 3** (1er, 2e, 3e selon l’ordre
   d’élimination) avec une colonne `rang` dans `participations`.
7 ter. **Meilleur score solo** dans le classement (aujourd’hui, « meilleur
   score » compte seulement les parties multijoueur).
8. **Interpolation** côté client : dessiner entre deux états reçus pour un
   mouvement plus fluide quand le réseau est lent. *NSI : calcul de positions
   intermédiaires (moyenne pondérée).*
9. **Normaliser les skins** : table `skins` + table d’association
   `skins_possedes(utilisateur_id, skin_id)` au lieu du texte `"blanc,rouge"`.
   *NSI : première forme normale, relation plusieurs-à-plusieurs.*

## Priorité 3 : pour aller plus loin

10. **Anti-farm du multijoueur** : ne pas payer de coins si deux comptes viennent de
    la même adresse IP, ou si la partie dure moins de 10 s. *NSI : conditions
    côté serveur.*
11. **Chat texte** dans la salle (messages échappés, longueur limitée).
    *NSI : nouvel événement, sécurité XSS.*
12. **Héberger la bibliothèque Socket.IO** dans `static/` au lieu du CDN, pour
    que le site marche sans Internet extérieur (ex. au lycée).
13. **Déconnexion en POST** avec jeton CSRF (aujourd’hui c’est un lien GET).
14. **Serveur de production** (gunicorn / eventlet) et HTTPS, au lieu du serveur
    de développement de Flask.
15. **Tests des routes Flask** avec `app.test_client()` en plus des tests du moteur.
