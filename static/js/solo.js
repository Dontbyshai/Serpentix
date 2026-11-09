/**
 * solo.js — Mode solo : toute la partie tourne dans le navigateur.
 *
 * Les réglages (vitesse, taille du plateau, durées des bonus…) ne sont PAS
 * recopiés ici : Flask les injecte dans la page (window.SERPENTIX_REGLAGES,
 * voir solo.html et game_engine.reglages_client()). Le solo va donc toujours
 * à la même vitesse que le multijoueur.
 * Bonus du solo : turbo, bouclier, fantôme, aimant (ciseaux et gel n'ont pas
 * de sens sans adversaire).
 * À la fin, on envoie le score au serveur qui crédite les coins
 * (le serveur vérifie que le score est plausible : voir app.py, api_solo_fin).
 */
(function () {
  const canvas = document.getElementById("solo-canvas");
  if (!canvas) return;                      // pas sur la page solo : on ne fait rien

  // --- Éléments de la page ---------------------------------------------------
  const scoreEl = document.getElementById("solo-score");
  const gainEl = document.getElementById("solo-gain");
  const effetsEl = document.getElementById("mes-effets");
  const btnRestart = document.getElementById("solo-restart");
  const btnAgain = document.getElementById("solo-again");
  const SKIN = window.SERPENTIX_SKIN || "#ffffff";   // couleur du skin équipé
  // Jeton anti-CSRF lu dans <meta name="csrf-token"> (voir base.html)
  const CSRF = document.querySelector('meta[name="csrf-token"]').content;

  // --- Réglages (venus de game_engine.py) -------------------------------------
  const R = window.SERPENTIX_REGLAGES;
  const COLS = R.largeur, ROWS = R.hauteur;
  const TPS = R.ticks_par_seconde;          // LA vitesse du jeu (pas par seconde)
  const TICK_MS = 1000 / TPS;
  const TYPES_BONUS = Object.keys(R.bonus);
  const COINS_MAX = 80;                     // plafond affiché (le serveur l'applique aussi)
  // Durées en secondes (pour les barres du HUD)
  const DUREES = {};
  TYPES_BONUS.forEach(function (t) { DUREES[t] = R.bonus[t].duree / TPS; });

  // --- État de la partie -------------------------------------------------------
  let corps, direction, file, pommes, bonus, score, vivant, bouclier, effets,
    grandir, decompte, enPause, timer, ticks;

  /** Remet tout à zéro et lance une nouvelle partie. */
  function reset() {
    const y = Math.floor(ROWS / 2);
    corps = [];
    for (let i = 0; i < R.taille_depart; i++) corps.push([8 - i, y]);   // tête = corps[0]
    direction = [1, 0];
    file = [];                              // virages en attente (comme le serveur)
    score = 0;
    vivant = true;
    bouclier = false;
    effets = { turbo: 0, fantome: 0, aimant: 0 };   // ticks restants de chaque effet
    grandir = 0;
    decompte = R.decompte;
    enPause = false;
    ticks = 0;
    pommes = [];
    bonus = [];
    Fin.cacher();
    placerPommes();
    placerBonus();
    afficherScore();
    clearInterval(timer);
    timer = setInterval(tick, TICK_MS);
    Controles.verrouiller();                // la page ne défile plus pendant la partie
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
    while (pommes.length < R.nb_pommes) {
      const c = caseLibre();
      if (!c) break;
      pommes.push(c);
    }
  }

  /** Tire un type de bonus en respectant les poids (comme tirer_type_bonus en Python). */
  function tirerType() {
    let total = 0;
    TYPES_BONUS.forEach(function (t) { total += R.bonus[t].poids; });
    let r = Math.random() * total;
    for (const t of TYPES_BONUS) {
      r -= R.bonus[t].poids;
      if (r < 0) return t;
    }
    return TYPES_BONUS[0];
  }

  function placerBonus() {
    while (bonus.length < R.nb_bonus) {
      const c = caseLibre();
      if (!c) break;
      bonus.push({ pos: c, type: tirerType() });
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

  /** @returns {boolean} vrai si la case est un mur, ou dans le corps (sauf en fantôme) */
  function estMortelle(c) {
    if (c[0] < 0 || c[1] < 0 || c[0] >= COLS || c[1] >= ROWS) return true;
    if (effets.fantome > 0) return false;   // le fantôme traverse son propre corps
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
      const type = bonus[j].type;
      if (type === "bouclier") bouclier = true;
      else effets[type] = R.bonus[type].duree;
      bonus.splice(j, 1);
    }
    return true;
  }

  /** Aimant : chaque pomme proche avance d'une case vers la tête (comme _attirer_pommes). */
  function attirerPommes() {
    if (effets.aimant <= 0) return;
    const o = new Set(corps.map(function (p) { return p[0] + "," + p[1]; }));
    const h = corps[0];
    pommes.forEach(function (p, i) {
      const ex = h[0] - p[0], ey = h[1] - p[1];
      if (Math.abs(ex) + Math.abs(ey) > R.rayon_aimant) return;
      const c = Math.abs(ex) >= Math.abs(ey) ? [p[0] + Math.sign(ex), p[1]] : [p[0], p[1] + Math.sign(ey)];
      const libre = !o.has(c[0] + "," + c[1]) &&
        !pommes.some(function (q) { return q[0] === c[0] && q[1] === c[1]; });
      if (libre) pommes[i] = c;
    });
  }

  /** Un tour de jeu (TPS fois par seconde). */
  function tick() {
    if (!vivant || enPause) return;
    if (decompte > 0) { decompte--; dessiner(); return; }
    ticks++;
    const pas = effets.turbo > 0 ? R.pas_turbo : 1;   // turbo = 2 cases par tour
    for (let k = 0; k < pas; k++) {
      if (!unPas()) { finDePartie(); return; }
    }
    attirerPommes();
    Object.keys(effets).forEach(function (n) { if (effets[n] > 0) effets[n]--; });
    placerPommes();
    if (ticks % R.recharge_bonus === 0) placerBonus();   // comme le serveur
    dessiner();
  }

  /** Arrête la partie et demande les coins au serveur. */
  async function finDePartie() {
    vivant = false;
    clearInterval(timer);
    dessiner();
    let message = "Score " + score;
    try {
      const res = await fetch("/api/solo/fin", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF },
        body: JSON.stringify({ score: score }),
      });
      const data = await res.json();
      if (data.ok) {
        gainEl.textContent = String(data.gain);
        message += " · +" + data.gain + " coins (solde " + data.coins + ")";
        // Met à jour le compteur de coins du menu sans recharger la page
        const navCoins = document.querySelector(".nav-coins");
        if (navCoins) navCoins.textContent = "◈ " + data.coins;
      } else {
        message += " · " + (data.erreur || "coins non crédités");
      }
    } catch (e) {
      message += " (coins non crédités : réseau)";
    }
    Fin.afficher({ type: "defaite", titre: "GAME OVER", message: message });
  }

  /** Dessine avec le module partagé dessin.js (même rendu que le multijoueur). */
  function dessiner() {
    const etatSerpent = {
      corps: corps, couleur: SKIN, vivant: vivant, bouclier: bouclier,
      fantome: effets.fantome > 0, effets: {},
    };
    Object.keys(effets).forEach(function (n) {
      if (effets[n] > 0) etatSerpent.effets[n] = effets[n] / TPS;   // en secondes
    });
    Dessin.plateau(canvas, {
      largeur: COLS, hauteur: ROWS, pommes: pommes, bonus: bonus, serpents: [etatSerpent],
    });
    if (effetsEl) Dessin.effetsHUD(effetsEl, etatSerpent, DUREES);
    if (decompte > 0) Dessin.texteCentre(canvas, String(Math.ceil(decompte / TPS)));
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
