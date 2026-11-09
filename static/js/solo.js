/**
 * solo.js — Mode solo : toute la partie tourne dans le navigateur.
 *
 * Les règles sont les MÊMES que celles du serveur (game_engine.py) :
 * grille 40 x 30, 10 tours par seconde, 3 pommes, turbo et bouclier.
 * À la fin, on envoie le score au serveur qui crédite les coins
 * (le serveur vérifie que le score est plausible : voir app.py, api_solo_fin).
 */
(function () {
  const canvas = document.getElementById("solo-canvas");
  if (!canvas) return;                      // pas sur la page solo : on ne fait rien

  // --- Éléments de la page ---------------------------------------------------
  const scoreEl = document.getElementById("solo-score");
  const gainEl = document.getElementById("solo-gain");
  const btnRestart = document.getElementById("solo-restart");
  const btnAgain = document.getElementById("solo-again");
  const overlay = document.getElementById("fin-overlay");
  const finMsg = document.getElementById("fin-msg");
  const SKIN = window.SERPENTIX_SKIN || "#ffffff";   // couleur du skin équipé
  // Jeton anti-CSRF lu dans <meta name="csrf-token"> (voir base.html)
  const CSRF = document.querySelector('meta[name="csrf-token"]').content;

  // --- Constantes (identiques à game_engine.py) ------------------------------
  const COLS = 40, ROWS = 30;
  const TICK_MS = 100;            // 10 tours par seconde
  const DUREE_TURBO = 30;         // 3 s
  const DECOMPTE = 30;            // 3 s de compte à rebours
  const COINS_MAX = 80;           // plafond affiché (le serveur l'applique aussi)

  // --- État de la partie -------------------------------------------------------
  let corps, direction, file, pommes, bonus, score, vivant, bouclier, turbo,
    grandir, decompte, enPause, timer;

  /** Remet tout à zéro et lance une nouvelle partie. */
  function reset() {
    corps = [[8, 15], [7, 15], [6, 15]];   // tête = corps[0]
    direction = [1, 0];
    file = [];                              // virages en attente (comme le serveur)
    score = 0;
    vivant = true;
    bouclier = false;
    turbo = 0;
    grandir = 0;
    decompte = DECOMPTE;
    enPause = false;
    pommes = [];
    bonus = [];
    overlay.classList.add("hidden");
    placerPommes();
    placerBonus();
    afficherScore();
    clearInterval(timer);
    timer = setInterval(tick, TICK_MS);
    // On prévient le serveur que la partie commence (il note l'heure)
    fetch("/api/solo/debut", { method: "POST", headers: { "X-CSRF-Token": CSRF } })
      .catch(function () { /* hors-ligne : la partie ne rapportera pas de coins */ });
    dessiner();
  }

  /** @returns {Set<string>} cases occupées, sous forme de texte "x,y" */
  function occupees() {
    const s = new Set(corps.map(function (p) { return p[0] + "," + p[1]; }));
    pommes.forEach(function (p) { s.add(p[0] + "," + p[1]); });
    bonus.forEach(function (b) { s.add(b.pos[0] + "," + b.pos[1]); });
    return s;
  }

  /** @returns {number[]|null} une case libre au hasard, ou null */
  function caseLibre() {
    const o = occupees();
    const libres = [];
    for (let y = 0; y < ROWS; y++) {
      for (let x = 0; x < COLS; x++) {
        if (!o.has(x + "," + y)) libres.push([x, y]);
      }
    }
    return libres.length ? libres[Math.floor(Math.random() * libres.length)] : null;
  }

  function placerPommes() {
    while (pommes.length < 3) {
      const c = caseLibre();
      if (!c) break;
      pommes.push(c);
    }
  }

  function placerBonus() {
    while (bonus.length < 2) {
      const c = caseLibre();
      if (!c) break;
      bonus.push({ pos: c, type: Math.random() < 0.5 ? "turbo" : "bouclier" });
    }
  }

  function afficherScore() {
    scoreEl.textContent = String(score);
    gainEl.textContent = String(Math.min(score, COINS_MAX));
  }

  /**
   * Mémorise un virage (appelée par controles.js).
   * @param {number} dx
   * @param {number} dy
   */
  function changerDirection(dx, dy) {
    if (!vivant || enPause) return;
    const ref = file.length ? file[file.length - 1] : direction;
    if (dx === ref[0] && dy === ref[1]) return;     // déjà cette direction
    if (dx === -ref[0] && dy === -ref[1]) return;   // demi-tour interdit
    if (file.length < 2) file.push([dx, dy]);
  }

  /** @returns {boolean} vrai si la case est un mur ou dans le corps (hors tête) */
  function estMortelle(c) {
    if (c[0] < 0 || c[1] < 0 || c[0] >= COLS || c[1] >= ROWS) return true;
    return corps.slice(1).some(function (p) { return p[0] === c[0] && p[1] === c[1]; });
  }

  /** Avance d'une case. @returns {boolean} faux si le serpent est mort */
  function unPas() {
    const sauvegarde = { corps: corps.slice(), grandir: grandir };
    if (file.length) direction = file.shift();
    const tete = [corps[0][0] + direction[0], corps[0][1] + direction[1]];
    corps.unshift(tete);
    if (grandir > 0) grandir--;
    else corps.pop();                       // la queue avance aussi

    if (estMortelle(tete)) {
      if (!bouclier) return false;
      // Bouclier : on annule le pas puis on tourne vers une case libre
      bouclier = false;
      corps = sauvegarde.corps;
      grandir = sauvegarde.grandir;
      file = [];
      const perp = [[direction[1], -direction[0]], [-direction[1], direction[0]]];
      for (const d of perp) {
        const c = [corps[0][0] + d[0], corps[0][1] + d[1]];
        if (!estMortelle(c)) { direction = d; break; }
      }
      return true;
    }

    // Pomme mangée ?
    const i = pommes.findIndex(function (p) { return p[0] === tete[0] && p[1] === tete[1]; });
    if (i >= 0) {
      pommes.splice(i, 1);
      score++;
      grandir++;
      afficherScore();
    }
    // Bonus attrapé ?
    const j = bonus.findIndex(function (b) { return b.pos[0] === tete[0] && b.pos[1] === tete[1]; });
    if (j >= 0) {
      if (bonus[j].type === "turbo") turbo = DUREE_TURBO;
      else bouclier = true;
      bonus.splice(j, 1);
    }
    return true;
  }

  /** Un tour de jeu (toutes les 100 ms). */
  function tick() {
    if (!vivant || enPause) return;
    if (decompte > 0) { decompte--; dessiner(); return; }
    const pas = turbo > 0 ? 2 : 1;          // turbo = 2 cases par tour
    for (let k = 0; k < pas; k++) {
      if (!unPas()) { finDePartie(); return; }
    }
    if (turbo > 0) turbo--;
    placerPommes();
    if (Math.random() < 0.02) placerBonus(); // ≈ 1 bonus toutes les 5 s
    dessiner();
  }

  /** Arrête la partie et demande les coins au serveur. */
  async function finDePartie() {
    vivant = false;
    clearInterval(timer);
    dessiner();
    overlay.classList.remove("hidden");
    finMsg.textContent = "Score " + score + "…";
    try {
      const res = await fetch("/api/solo/fin", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF },
        body: JSON.stringify({ score: score }),
      });
      const data = await res.json();
      if (data.ok) {
        gainEl.textContent = String(data.gain);
        finMsg.textContent = "Score " + score + " · +" + data.gain + " coins (solde " + data.coins + ")";
        // Met à jour le compteur de coins du menu sans recharger la page
        const navCoins = document.querySelector(".nav-coins");
        if (navCoins) navCoins.textContent = "◈ " + data.coins;
      } else {
        finMsg.textContent = "Score " + score + " · " + (data.erreur || "coins non crédités");
      }
    } catch (e) {
      finMsg.textContent = "Score " + score + " (coins non crédités : réseau)";
    }
  }

  /** Dessine avec le module partagé dessin.js (même rendu que le 1v1). */
  function dessiner() {
    Dessin.plateau(canvas, {
      largeur: COLS, hauteur: ROWS, pommes: pommes, bonus: bonus,
      serpents: [{ corps: corps, couleur: SKIN, vivant: vivant, bouclier: bouclier }],
    });
    if (decompte > 0) Dessin.texteCentre(canvas, String(Math.ceil(decompte / 10)));
    else if (enPause) Dessin.texteCentre(canvas, "PAUSE");
  }

  // Contrôles (clavier, glisser, boutons) + pause avec Espace ou P
  Controles.brancher(canvas, changerDirection);
  window.addEventListener("keydown", function (ev) {
    if ((ev.key === " " || ev.key === "p" || ev.key === "P") && vivant) {
      ev.preventDefault();
      enPause = !enPause;
      dessiner();
    }
  });

  btnRestart.addEventListener("click", reset);
  btnAgain.addEventListener("click", reset);
  reset();
})();
