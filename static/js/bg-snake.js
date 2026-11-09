/**
 * bg-snake.js — Animation décorative : un serpent qui « joue tout seul »
 * derrière le site (sur la page d'accueil, la boutique, etc.).
 *
 * - Non interactif (pointer-events: none dans le CSS).
 * - 100 % noir & blanc, SANS transparence : le corps est dessiné en simples
 *   contours blancs (fin et discret) et la tête est pleine.
 * - Pilotage automatique : à chaque pas, le serpent choisit parmi les directions
 *   possibles celle qui le rapproche le plus de la pomme (algorithme glouton).
 * - Désactivé sur les pages de jeu (classe no-bg-snake sur <body>).
 */
(function () {
  const canvas = document.getElementById("bg-snake");
  if (!canvas || !canvas.getContext) return;
  if (document.body.classList.contains("no-bg-snake")) {
    canvas.remove();                        // pages de jeu : pas de décor
    return;
  }
  // Respecte le réglage « réduire les animations » du système (accessibilité)
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    canvas.remove();
    return;
  }

  const ctx = canvas.getContext("2d");
  const CELL = 22;           // taille d'une case en pixels
  const STEP_MS = 110;       // un pas toutes les 110 ms
  const TAILLE_MAX = 28;     // le serpent décoratif ne grandit pas au-delà
  let w = 0, h = 0, cols = 0, rows = 0, ox = 0, oy = 0;
  let snake = [];            // liste de {x, y}, tête = snake[0]
  let dir = { x: 1, y: 0 };
  let apple = { x: 0, y: 0 };
  let last = 0;

  /** Adapte la grille à la taille de la fenêtre. */
  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
    cols = Math.max(20, Math.floor(w / CELL));
    rows = Math.max(14, Math.floor(h / CELL));
    ox = (w - cols * CELL) / 2;  // marges pour centrer la grille
    oy = (h - rows * CELL) / 2;
    if (!snake.length) {
      reset();
    } else {
      // On ramène tout dans la nouvelle grille (modulo = « wrap »)
      apple.x %= cols;
      apple.y %= rows;
      snake = snake.map(function (s) { return { x: s.x % cols, y: s.y % rows }; });
    }
  }

  /** Repart avec un petit serpent au centre. */
  function reset() {
    const cx = Math.floor(cols / 2);
    const cy = Math.floor(rows / 2);
    snake = [];
    for (let i = 0; i < 5; i++) snake.push({ x: cx - i, y: cy });
    dir = { x: 1, y: 0 };
    placeApple();
  }

  /** Place la pomme sur une case libre au hasard. */
  function placeApple() {
    for (let essais = 0; essais < 200; essais++) {
      apple = { x: Math.floor(Math.random() * cols), y: Math.floor(Math.random() * rows) };
      if (!snake.some(function (s) { return s.x === apple.x && s.y === apple.y; })) return;
    }
  }

  /**
   * Distance de Manhattan en tenant compte du « wrap » (les bords se
   * rejoignent, comme dans un vieux Snake).
   * @returns {number}
   */
  function wrapDist(ax, ay, bx, by) {
    let dx = Math.abs(ax - bx);
    let dy = Math.abs(ay - by);
    dx = Math.min(dx, cols - dx);
    dy = Math.min(dy, rows - dy);
    return dx + dy;
  }

  /** Choisit la prochaine direction (glouton + un peu de hasard). */
  function choisirDirection() {
    const head = snake[0];
    let best = null;
    let bestScore = Infinity;
    [{ x: 1, y: 0 }, { x: -1, y: 0 }, { x: 0, y: 1 }, { x: 0, y: -1 }].forEach(function (c) {
      if (c.x === -dir.x && c.y === -dir.y) return;           // pas de demi-tour
      const nx = (head.x + c.x + cols) % cols;
      const ny = (head.y + c.y + rows) % rows;
      if (snake.some(function (s, i) { return i < snake.length - 1 && s.x === nx && s.y === ny; })) return;
      const score = wrapDist(nx, ny, apple.x, apple.y) + Math.random() * 0.4;
      if (score < bestScore) { bestScore = score; best = c; }
    });
    if (best) dir = best;
  }

  /** Avance d'une case (mange la pomme si besoin). */
  function step() {
    choisirDirection();
    const head = snake[0];
    const nx = (head.x + dir.x + cols) % cols;
    const ny = (head.y + dir.y + rows) % rows;
    if (snake.some(function (s) { return s.x === nx && s.y === ny; })) { reset(); return; }
    snake.unshift({ x: nx, y: ny });
    if (nx === apple.x && ny === apple.y) {
      placeApple();
      if (snake.length > TAILLE_MAX) snake.pop();
    } else {
      snake.pop();
    }
  }

  /** Dessine la frame : uniquement noir et blanc, aucune transparence. */
  function draw() {
    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = "#ffffff";
    ctx.fillStyle = "#ffffff";
    ctx.lineWidth = 1;

    // Pomme : petit cercle (contour)
    ctx.beginPath();
    ctx.arc(apple.x * CELL + ox + CELL / 2, apple.y * CELL + oy + CELL / 2, CELL * 0.25, 0, Math.PI * 2);
    ctx.stroke();

    // Serpent : tête pleine, corps en contours fins
    snake.forEach(function (s, i) {
      const x = s.x * CELL + ox + 4;
      const y = s.y * CELL + oy + 4;
      const size = CELL - 8;
      if (i === 0) ctx.fillRect(x, y, size, size);
      else ctx.strokeRect(x + 0.5, y + 0.5, size - 1, size - 1);
    });
  }

  /** Boucle d'animation : requestAnimationFrame ≈ 60 fois par seconde. */
  function loop(ts) {
    if (!last) last = ts;
    if (ts - last >= STEP_MS) {
      step();
      last = ts;
      draw();
    }
    requestAnimationFrame(loop);
  }

  window.addEventListener("resize", function () { resize(); draw(); });
  resize();
  draw();
  requestAnimationFrame(loop);
})();
