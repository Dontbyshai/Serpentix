/**
 * game.js — Client d'une partie multijoueur (2 ou 3 joueurs) : canvas + Socket.IO.
 *
 * Le navigateur ne calcule RIEN des règles : il envoie seulement les touches
 * au serveur (événement « direction ») et redessine l'état reçu à chaque tick
 * (événement « etat_jeu »). C'est le modèle « serveur autoritaire » :
 * impossible de tricher en modifiant ce fichier.
 *
 * Événements Socket.IO utilisés :
 *   envoyés : rejoindre_salle {code}, direction {code, dx, dy}, quitter_salle {code}
 *   reçus   : etat_jeu {...}, partie_lancee {code}, erreur {message}
 */
(function () {
  const canvas = document.getElementById("game");
  if (!canvas) return;
  const statusEl = document.getElementById("game-status");
  const scoresEl = document.getElementById("scores");
  const mesEffetsEl = document.getElementById("mes-effets");
  const journalEl = document.getElementById("journal");
  const code = window.SERPENTIX_CODE;      // code de la salle (injecté par le template)
  const MOI = window.SERPENTIX_MOI;        // id de l'utilisateur connecté
  const DUREES = window.SERPENTIX_DUREES || {};   // durée de chaque effet (s), pour les barres
  let finAffichee = false;                 // l'écran de fin n'est montré qu'une fois

  // Connexion temps réel : WebSocket si possible, sinon « long polling »
  const socket = io({ transports: ["websocket", "polling"] });

  socket.on("connect", function () {
    statusEl.textContent = "Connecté · salle " + code;
    socket.emit("rejoindre_salle", { code: code });
  });

  socket.on("disconnect", function () {
    statusEl.textContent = "Connexion perdue… reconnexion";
  });

  socket.on("erreur", function (data) {
    statusEl.textContent = data.message || "Erreur";
  });

  socket.on("partie_lancee", function () {
    statusEl.textContent = "C'est parti !";
  });

  /** Reçu à chaque tick : on met à jour le texte, les scores et le dessin. */
  socket.on("etat_jeu", function (etat) {
    const moi = (etat.serpents || []).find(function (s) { return s.joueur_id === MOI; });
    if (etat.statut === "attente") {
      const manque = etat.max_joueurs - etat.nb_joueurs;
      statusEl.textContent = "Salle " + etat.nb_joueurs + "/" + etat.max_joueurs +
        " · il manque " + manque + " joueur" + (manque > 1 ? "s" : "") + " · code " + etat.code;
    } else if (etat.statut === "en_cours") {
      // Le verrou de défilement s'active dès que la partie est lancée
      Controles.verrouiller();
      if (etat.decompte > 0) statusEl.textContent = "Départ dans " + etat.decompte + "…";
      else if (moi && !moi.vivant) statusEl.textContent = "Éliminé · tu regardes la fin";
      else statusEl.textContent = "En cours · " + etat.max_joueurs + " joueurs";
    } else if (etat.statut === "terminee") {
      statusEl.textContent = "Terminée";
      montrerFin(etat);
    }
    afficherScores(etat);
    if (mesEffetsEl) Dessin.effetsHUD(mesEffetsEl, moi || {}, DUREES);
    (etat.evenements || []).forEach(ajouterJournal);
    Dessin.plateau(canvas, etat);
    if (etat.statut === "en_cours" && etat.decompte > 0) {
      Dessin.texteCentre(canvas, String(etat.decompte));
    } else if (etat.statut === "attente") {
      Dessin.texteCentre(canvas, etat.code);
    }
  });

  /**
   * Choisit et affiche le bon écran de fin (victoire / défaite / nul).
   * @param {Object} etat - état final reçu du serveur
   */
  function montrerFin(etat) {
    if (finAffichee) return;
    finAffichee = true;
    let type, titre;
    if (etat.vainqueur_id === MOI) { type = "victoire"; titre = "VICTOIRE"; }
    else if (etat.vainqueur_id === null || etat.vainqueur_id === undefined) { type = "nul"; titre = "MATCH NUL"; }
    else { type = "defaite"; titre = "DÉFAITE"; }
    Fin.afficher({
      type: type, titre: titre,
      message: etat.message_fin || "Fin de partie",
      couleur: etat.vainqueur_couleur,
    });
  }

  /**
   * Ajoute une ligne en haut du petit journal (« X coupe la queue de Y »).
   * @param {string} texte
   */
  function ajouterJournal(texte) {
    if (!journalEl) return;
    const li = document.createElement("li");
    li.textContent = texte;                  // textContent : pas d'injection HTML
    journalEl.prepend(li);
    while (journalEl.children.length > 4) journalEl.lastChild.remove();
  }

  /**
   * Affiche une « pastille » par joueur : couleur, pseudo, score, effets.
   * On construit les éléments avec textContent (jamais innerHTML avec des
   * données reçues) : un pseudo piégé ne pourrait pas injecter du HTML (XSS).
   * @param {Object} etat - état reçu du serveur
   */
  function afficherScores(etat) {
    scoresEl.textContent = "";
    (etat.serpents || []).forEach(function (s) {
      const pill = document.createElement("div");
      pill.className = "score-pill" + (s.joueur_id === MOI ? " moi" : "") + (s.vivant ? "" : " mort");
      const swatch = document.createElement("span");
      swatch.className = "swatch";
      swatch.style.background = s.couleur;
      const nom = document.createElement("strong");
      nom.textContent = s.pseudo + (s.joueur_id === MOI ? " (toi)" : "");
      const score = document.createElement("span");
      score.textContent = " " + s.score + (s.vivant ? "" : " ×");
      pill.appendChild(swatch);
      pill.appendChild(nom);
      pill.appendChild(score);
      // Pictogrammes des effets actifs de ce joueur
      Object.keys(s.effets || {}).concat(s.bouclier ? ["bouclier"] : []).forEach(function (nomEffet) {
        pill.appendChild(Dessin.icone(nomEffet, 14));
      });
      scoresEl.appendChild(pill);
    });
  }

  // Chaque virage part tout de suite au serveur, qui le met dans une file
  Controles.brancher(canvas, function (dx, dy) {
    socket.emit("direction", { code: code, dx: dx, dy: dy });
  });

  // Fermer l'onglet = quitter la salle (forfait si la partie a commencé)
  window.addEventListener("beforeunload", function () {
    socket.emit("quitter_salle", { code: code });
  });
})();
