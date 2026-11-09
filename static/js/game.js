/**
 * game.js — Client du duel 1v1 (canvas + Socket.IO).
 *
 * Le navigateur ne calcule RIEN des règles : il envoie seulement les touches
 * au serveur (événement « direction ») et redessine l'état reçu 10 fois par
 * seconde (événement « etat_jeu »). C'est le modèle « serveur autoritaire » :
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
  const overlay = document.getElementById("fin-overlay");
  const finMsg = document.getElementById("fin-msg");
  const code = window.SERPENTIX_CODE;      // code de la salle (injecté par le template)
  const MOI = window.SERPENTIX_MOI;        // id de l'utilisateur connecté

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

  /** Reçu 10 fois par seconde : on met à jour le texte, les scores et le dessin. */
  socket.on("etat_jeu", function (etat) {
    if (etat.statut === "attente") {
      statusEl.textContent = "En attente d'un adversaire (" + etat.nb_joueurs + "/2) · envoie le code " + etat.code;
    } else if (etat.statut === "en_cours") {
      statusEl.textContent = etat.decompte > 0 ? "Départ dans " + etat.decompte + "…" : "En cours";
    } else if (etat.statut === "terminee") {
      statusEl.textContent = "Terminée";
      finMsg.textContent = etat.message_fin || "Fin de partie";
      overlay.classList.remove("hidden");
    }
    afficherScores(etat);
    Dessin.plateau(canvas, etat);
    if (etat.statut === "en_cours" && etat.decompte > 0) {
      Dessin.texteCentre(canvas, String(etat.decompte));
    } else if (etat.statut === "attente") {
      Dessin.texteCentre(canvas, etat.code);
    }
  });

  /**
   * Affiche une « pastille » par joueur : couleur, pseudo, score, bonus.
   * On construit les éléments avec textContent (jamais innerHTML avec des
   * données reçues) : un pseudo piégé ne pourrait pas injecter du HTML (XSS).
   * @param {Object} etat - état reçu du serveur
   */
  function afficherScores(etat) {
    scoresEl.textContent = "";
    (etat.serpents || []).forEach(function (s) {
      const pill = document.createElement("div");
      pill.className = "score-pill";
      const swatch = document.createElement("span");
      swatch.className = "swatch";
      swatch.style.background = s.couleur;
      const nom = document.createElement("strong");
      nom.textContent = s.pseudo + (s.joueur_id === MOI ? " (toi)" : "");
      pill.appendChild(swatch);
      pill.appendChild(nom);
      pill.appendChild(document.createTextNode(
        " " + s.score + (s.bouclier ? " ○" : "") + (s.turbo ? " △" : "") + (s.vivant ? "" : " ×")
      ));
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
