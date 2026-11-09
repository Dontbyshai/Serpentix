/**
 * bg-snake.js — « Arène » animée derrière l'accueil et la page Jouer.
 *
 * Plusieurs serpents pilotés par l'ordinateur jouent tout seuls en fond :
 * ils chassent les pommes, grandissent, se percutent, explosent en pommes
 * (comme dans Slither) puis réapparaissent au bord de l'écran.
 *
 * - Activé seulement si <body> a la classe « avec-arene » (accueil, Jouer).
 * - Non interactif (pointer-events: none dans le CSS) : on ne peut pas cliquer dessus.
 * - 100 % noir & blanc, sans transparence ; les serpents ont les couleurs des
 *   skins de la boutique (seules couleurs autorisées).
 * - Léger pour le processeur : requestAnimationFrame limité à ~30 images/s,
 *   et l'animation s'ARRÊTE quand l'onglet est caché (visibilitychange).
 * - Accessibilité : si le système demande « réduire les animations », on
 *   dessine une seule image fixe.
 *
 * Pilotage des serpents (algorithme glouton) : à chaque pas, parmi les directions
 * qui ne tuent pas tout de suite, on prend celle qui rapproche le plus de la
 * pomme visée (avec un peu de hasard pour que ce soit vivant).
 */
(function () {
  const canvas = document.getElementById("bg-snake");
  if (!canvas || !canvas.getContext) return;
  if (!document.body.classList.contains("avec-arene")) {
    canvas.remove();                        // autres pages : fond noir uni
    return;
  }
  const reduire = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const ctx = canvas.getContext("2d");
  const CELL = 22;              // taille d'une case en pixels
  const PAS_MS = 120;           // un pas de jeu toutes les 120 ms
  const IMAGE_MS = 33;          // ~30 images par seconde maximum
  const TAILLE_MAX = 34;        // au-delà le serpent ne grandit plus
  const RESPAWN_MS = 1600;      // temps avant de réapparaître après une explosion
  const COULEURS = ["#ffffff", "#ef4444", "#22c55e", "#f97316", "#eab308"];
  const DIRS = [[1, 0], [-1, 0], [0, 1], [0, -1]];

  let cols = 0, rows = 0, ox = 0, oy = 0;
  let serpents = [];            // {corps:[[x,y]...], dir, couleur, grandir, mortA}
  let pommes = [];              // [[x,y], ...]
  let eclats = [];              // petits carrés d'explosion {x, y, vx, vy, vie, couleur}
  let dernierPas = 0, derniereImage = 0, animation = null;

  /** Adapte la grille à la taille de la fenêtre (et à l'écran Retina). */
  function redimensionner() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(window.innerWidth * dpr);
    canvas.height = Math.floor(window.innerHeight * dpr);
    canvas.style.width = window.innerWidth + "px";
    canvas.style.height = window.innerHeight + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    cols = Math.max(16, Math.floor(window.innerWidth / CELL));
    rows = Math.max(12, Math.floor(window.innerHeight / CELL));
    // Petit décalage pour centrer la grille dans la fenêtre
    ox = Math.floor((window.innerWidth - cols * CELL) / 2);
    oy = Math.floor((window.innerHeight - rows * CELL) / 2);
    initialiser();
  }

  /** Crée les serpents et les pommes (nombre adapté à la taille de l'écran). */
  function initialiser() {
    const nbSerpents = cols * rows > 1800 ? 9 : (cols * rows > 900 ? 7 : 5);
    serpents = [];
    for (let i = 0; i < nbSerpents; i++) {
      const s = { couleur: COULEURS[i % COULEURS.length], corps: [], dir: [1, 0], grandir: 0, mortA: 0 };
      naitre(s);
      serpents.push(s);
    }
    pommes = [];
    eclats = [];
    const nbPommes = Math.max(8, Math.floor((cols * rows) / 110));
    for (let i = 0; i < nbPommes; i++) ajouterPomme();
  }

  /** Fait (re)naître un serpent sur un bord, tourné vers l'intérieur. */
  function naitre(s) {
    const bord = Math.floor(Math.random() * 4);
    let x, y, d;
    if (bord === 0) { x = 0; y = rnd(rows); d = [1, 0]; }
    else if (bord === 1) { x = cols - 1; y = rnd(rows); d = [-1, 0]; }
    else if (bord === 2) { x = rnd(cols); y = 0; d = [0, 1]; }
    else { x = rnd(cols); y = rows - 1; d = [0, -1]; }
    s.corps = [[x, y]];
    s.dir = d;
    s.grandir = 7 + rnd(6);                 // il « sort » du bord en grandissant
    s.mortA = 0;
  }

  /** @returns {number} entier au hasard entre 0 et n-1 */
  function rnd(n) { return Math.floor(Math.random() * n); }

  /** Case suivante avec « bords qui bouclent » (sortir à droite = rentrer à gauche). */
  function suivante(c, d) {
    return [(c[0] + d[0] + cols) % cols, (c[1] + d[1] + rows) % rows];
  }

  /** @returns {Set<string>} toutes les cases occupées par un serpent vivant */
  function casesOccupees() {
    const o = new Set();
    serpents.forEach(function (s) {
      if (!s.mortA) s.corps.forEach(function (c) { o.add(c[0] + "," + c[1]); });
    });
    return o;
  }

  function ajouterPomme() {
    pommes.push([rnd(cols), rnd(rows)]);
  }

  /** Distance « torique » (en tenant compte des bords qui bouclent). */
  function distance(a, b) {
    const dx = Math.abs(a[0] - b[0]);
    const dy = Math.abs(a[1] - b[1]);
    return Math.min(dx, cols - dx) + Math.min(dy, rows - dy);
  }

  /** Choisit la direction d'un serpent (algorithme glouton + un peu de hasard). */
  function choisirDirection(s, occupees) {
    const tete = s.corps[0];
    let cible = null, dMin = Infinity;
    pommes.forEach(function (p) {
      const d = distance(tete, p);
      if (d < dMin) { dMin = d; cible = p; }
    });
    let meilleure = s.dir, score = Infinity;
    DIRS.forEach(function (d) {
      if (d[0] === -s.dir[0] && d[1] === -s.dir[1]) return;   // pas de demi-tour
      const c = suivante(tete, d);
      // 85 % du temps on évite les corps ; 15 % on « oublie » → collisions spectaculaires
      const danger = occupees.has(c[0] + "," + c[1]) && Math.random() < 0.85 ? 1000 : 0;
      const sc = (cible ? distance(c, cible) : 0) + danger + Math.random() * 1.5;
      if (sc < score) { score = sc; meilleure = d; }
    });
    s.dir = meilleure;
  }

  /** Explosion : le corps devient des pommes + éclats qui s'envolent. */
  function exploser(s, maintenant) {
    s.corps.forEach(function (c, i) {
      if (i % 2 === 0) pommes.push([c[0], c[1]]);
      if (eclats.length < 220) {
        eclats.push({
          x: ox + c[0] * CELL + CELL / 2, y: oy + c[1] * CELL + CELL / 2,
          vx: (Math.random() - 0.5) * 6, vy: (Math.random() - 0.5) * 6,
          vie: 18 + rnd(12), couleur: s.couleur,
        });
      }
    });
    s.mortA = maintenant;
    s.corps = [];
  }

  /** Un pas de jeu pour tous les serpents. */
  function pas(maintenant) {
    const occupees = casesOccupees();
    serpents.forEach(function (s) {
      if (s.mortA) {
        if (maintenant - s.mortA > RESPAWN_MS) naitre(s);   // réapparition
        return;
      }
      choisirDirection(s, occupees);
      const t = suivante(s.corps[0], s.dir);
      s.corps.unshift(t);
      if (s.grandir > 0) s.grandir--;
      else s.corps.pop();
    });
    // Collisions : tête dans un corps (le sien ou celui d'un autre)
    const morts = [];
    serpents.forEach(function (s) {
      if (s.mortA || !s.corps.length) return;
      const t = s.corps[0];
      serpents.forEach(function (autre) {
        if (autre.mortA) return;
        const debut = autre === s ? 1 : 0;
        for (let i = debut; i < autre.corps.length; i++) {
          if (autre.corps[i][0] === t[0] && autre.corps[i][1] === t[1]) {
            // Tête contre tête : le plus court explose (comme dans le vrai jeu)
            if (i === 0 && autre.corps.length > s.corps.length) { morts.push(s); return; }
            if (i === 0 && autre !== s) { morts.push(autre); return; }
            morts.push(s);
            return;
          }
        }
      });
    });
    morts.forEach(function (s) { if (!s.mortA) exploser(s, maintenant); });
    // Pommes mangées
    serpents.forEach(function (s) {
      if (s.mortA) return;
      const t = s.corps[0];
      const i = pommes.findIndex(function (p) { return p[0] === t[0] && p[1] === t[1]; });
      if (i >= 0) {
        pommes.splice(i, 1);
        if (s.corps.length < TAILLE_MAX) s.grandir += 2;
      }
    });
    // On garde toujours assez de pommes, sans en accumuler à l'infini
    const nbMin = Math.max(8, Math.floor((cols * rows) / 110));
    while (pommes.length < nbMin) ajouterPomme();
    if (pommes.length > nbMin * 3) pommes.splice(0, pommes.length - nbMin * 3);
  }

  /** Dessine une image complète de l'arène. */
  function dessiner(maintenant) {
    const W = window.innerWidth, H = window.innerHeight;
    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, W, H);
    // Grille très légère : un point blanc toutes les 4 cases
    ctx.fillStyle = "#ffffff";
    for (let y = 0; y < rows; y += 4) {
      for (let x = 0; x < cols; x += 4) ctx.fillRect(ox + x * CELL + CELL / 2, oy + y * CELL + CELL / 2, 1, 1);
    }
    // Pommes : disques blancs qui « respirent » (rayon qui varie, pas de transparence)
    pommes.forEach(function (p, i) {
      const r = CELL * (0.18 + 0.05 * Math.sin(maintenant / 260 + i));
      ctx.beginPath();
      ctx.arc(ox + p[0] * CELL + CELL / 2, oy + p[1] * CELL + CELL / 2, r, 0, Math.PI * 2);
      ctx.fill();
    });
    // Serpents : cases pleines de la couleur du skin, comme dans le vrai jeu.
    // La queue rétrécit un peu (les 4 dernières cases) pour un rendu plus vivant.
    serpents.forEach(function (s) {
      if (s.mortA) return;
      ctx.fillStyle = s.couleur;
      const n = s.corps.length;
      for (let i = n - 1; i >= 0; i--) {
        const c = s.corps[i];
        const px = ox + c[0] * CELL, py = oy + c[1] * CELL;
        const marge = i === 0 ? 1 : Math.min(7, 2 + Math.max(0, i - (n - 5)));
        ctx.fillRect(px + marge, py + marge, CELL - marge * 2, CELL - marge * 2);
      }
      // Yeux noirs sur la tête
      const t = s.corps[0];
      ctx.fillStyle = "#000000";
      const cx = ox + t[0] * CELL + CELL / 2, cy = oy + t[1] * CELL + CELL / 2;
      ctx.fillRect(cx + s.dir[0] * 4 - s.dir[1] * 4 - 2, cy + s.dir[1] * 4 + s.dir[0] * 4 - 2, 3, 3);
      ctx.fillRect(cx + s.dir[0] * 4 + s.dir[1] * 4 - 2, cy + s.dir[1] * 4 - s.dir[0] * 4 - 2, 3, 3);
    });
    // Éclats d'explosion
    eclats.forEach(function (e) {
      ctx.fillStyle = e.couleur;
      ctx.fillRect(e.x - 2, e.y - 2, 4, 4);
    });
  }

  /** Boucle d'animation : appelée par le navigateur avant chaque affichage. */
  function boucle(maintenant) {
    animation = requestAnimationFrame(boucle);
    if (maintenant - derniereImage < IMAGE_MS) return;      // limite à ~30 images/s
    derniereImage = maintenant;
    if (maintenant - dernierPas >= PAS_MS) {
      dernierPas = maintenant;
      pas(maintenant);
    }
    eclats.forEach(function (e) { e.x += e.vx; e.y += e.vy; e.vx *= 0.92; e.vy *= 0.92; e.vie--; });
    eclats = eclats.filter(function (e) { return e.vie > 0; });
    dessiner(maintenant);
  }

  function demarrer() {
    if (animation === null) animation = requestAnimationFrame(boucle);
  }
  function arreter() {
    if (animation !== null) cancelAnimationFrame(animation);
    animation = null;
  }

  redimensionner();
  let attente = null;
  window.addEventListener("resize", function () {
    clearTimeout(attente);                  // on attend la fin du redimensionnement
    attente = setTimeout(redimensionner, 150);
  });

  if (reduire) {
    // Une image fixe : quelques pas « pour de faux » puis on dessine
    for (let k = 0; k < 40; k++) pas(k * PAS_MS);
    dessiner(0);
    return;
  }
  // Onglet caché → on arrête complètement (0 % de processeur)
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) arreter();
    else demarrer();
  });
  demarrer();
})();
