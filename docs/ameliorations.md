# Améliorations possibles (non réalisées)

Liste classée par priorité. Chaque idée reste dans le cadre du programme de NSI.

## Priorité 1 : utile et faisable rapidement

1. **Bouton « Revanche »** à la fin d’un 1v1 : recrée une salle avec les deux
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

5. **File d’attente automatique** (« Partie rapide ») : le serveur associe deux
   joueurs qui attendent. *NSI : structure de données file (FIFO).*
6. **Mode spectateur** : rejoindre une salle pleine en lecture seule.
   *NSI : rooms Socket.IO, droits différents selon le rôle.*
7. **Vitesse qui augmente** avec la longueur, ou plateau qui rétrécit après
   2 minutes pour éviter les parties trop longues. *NSI : paramètres de l’algorithme.*
8. **Interpolation** côté client : dessiner entre deux états reçus pour un
   mouvement plus fluide quand le réseau est lent. *NSI : calcul de positions
   intermédiaires (moyenne pondérée).*
9. **Normaliser les skins** : table `skins` + table d’association
   `skins_possedes(utilisateur_id, skin_id)` au lieu du texte `"blanc,rouge"`.
   *NSI : première forme normale, relation plusieurs-à-plusieurs.*

## Priorité 3 : pour aller plus loin

10. **Anti-farm du 1v1** : ne pas payer de coins si les deux comptes viennent de
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
