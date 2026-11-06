/**
 * bg-snake.js — Animation décorative (serpent qui joue en arrière-plan).
 * Non interactive. Noir & blanc uniquement.
 */
(function () {
  if (document.body.classList.contains("no-bg-snake")) {
    const c = document.getElementById("bg-snake");
    if (c) c.remove();
    return;
  }
  const canvas = document.getElementById("bg-snake");
  if (!canvas || !canvas.getContext) return;

  const ctx = canvas.getContext("2d");
  let w = 0, h = 0, cell = 22, cols = 0, rows = 0;
  let snake = [];
  let dir = { x: 1, y: 0 };
  let nextDir = { x: 1, y: 0 };
  let apple = { x: 0, y: 0 };
  let tick = 0;
  let last = 0;
  const STEP_MS = 110;

  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
    cols = Math.max(20, Math.floor(w / cell));
    rows = Math.max(14, Math.floor(h / cell));
    // Recentrer la logique grille
    if (!snake.length) reset();
    else {
      // garder la pomme dans les bornes
      apple.x = apple.x % cols;
      apple.y = apple.y % rows;
      snake = snake.map((s) => ({ x: ((s.x % cols) + cols) % cols, y: ((s.y % rows) + rows) % rows }));
    }
  }

  function reset() {
    const cx = Math.floor(cols / 2);
    const cy = Math.floor(rows / 2);
    snake = [
      { x: cx, y: cy },
      { x: cx - 1, y: cy },
      { x: cx - 2, y: cy },
      { x: cx - 3, y: cy },
      { x: cx - 4, y: cy },
    ];
    dir = { x: 1, y: 0 };
    nextDir = { x: 1, y: 0 };
    placeApple();
  }

  function placeApple() {
    let ok = false;
    let tries = 0;
    while (!ok && tries < 200) {
      apple = {
        x: Math.floor(Math.random() * cols),
        y: Math.floor(Math.random() * rows),
      };
      ok = !snake.some((s) => s.x === apple.x && s.y === apple.y);
      tries++;
    }
  }

  function towardApple() {
    const head = snake[0];
    const dx = apple.x - head.x;
    const dy = apple.y - head.y;
    // wrap-aware distance
    let best = null;
    const candidates = [
      { x: 1, y: 0 },
      { x: -1, y: 0 },
      { x: 0, y: 1 },
      { x: 0, y: -1 },
    ];
    // ne pas faire demi-tour
    const filtered = candidates.filter((c) => !(c.x === -dir.x && c.y === -dir.y));

    function wrapDist(ax, ay, bx, by) {
      let dx2 = Math.abs(ax - bx);
      let dy2 = Math.abs(ay - by);
      dx2 = Math.min(dx2, cols - dx2);
      dy2 = Math.min(dy2, rows - dy2);
      return dx2 + dy2;
    }

    let bestScore = Infinity;
    for (const c of filtered) {
      const nx = (head.x + c.x + cols) % cols;
      const ny = (head.y + c.y + rows) % rows;
      // éviter de se mordre immédiatement
      if (snake.some((s, i) => i < snake.length - 1 && s.x === nx && s.y === ny)) continue;
      let score = wrapDist(nx, ny, apple.x, apple.y);
      // un peu d'aléa pour un mouvement plus vivant
      score += Math.random() * 0.4;
      if (score < bestScore) {
        bestScore = score;
        best = c;
      }
    }
    if (best) nextDir = best;
    else if (filtered.length) nextDir = filtered[Math.floor(Math.random() * filtered.length)];
  }

  function step() {
    towardApple();
    dir = nextDir;
    const head = snake[0];
    const nx = (head.x + dir.x + cols) % cols;
    const ny = (head.y + dir.y + rows) % rows;

    // collision corps → reset doux
    if (snake.some((s) => s.x === nx && s.y === ny)) {
      reset();
      return;
    }

    snake.unshift({ x: nx, y: ny });
    if (nx === apple.x && ny === apple.y) {
      placeApple();
      if (snake.length > 28) {
        // garder une taille raisonnable pour le décor
        snake.pop();
      }
    } else {
      snake.pop();
    }
  }

  function draw() {
    ctx.clearRect(0, 0, w, h);
    // Légère grille blanche très fine (traits 1px purs blancs, espacés)
    ctx.globalAlpha = 0.08;
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1;
    const stepG = cell * 2;
    ctx.beginPath();
    for (let x = 0; x < w; x += stepG) {
      ctx.moveTo(x + 0.5, 0);
      ctx.lineTo(x + 0.5, h);
    }
    for (let y = 0; y < h; y += stepG) {
      ctx.moveTo(0, y + 0.5);
      ctx.lineTo(w, y + 0.5);
    }
    ctx.stroke();

    // Pomme
    ctx.globalAlpha = 0.45;
    ctx.fillStyle = "#ffffff";
    const ax = apple.x * cell + (w - cols * cell) / 2;
    const ay = apple.y * cell + (h - rows * cell) / 2;
    const ox = (w - cols * cell) / 2;
    const oy = (h - rows * cell) / 2;
    ctx.beginPath();
    ctx.arc(
      apple.x * cell + ox + cell / 2,
      apple.y * cell + oy + cell / 2,
      cell * 0.28,
      0,
      Math.PI * 2
    );
    ctx.fill();

    // Serpent
    for (let i = 0; i < snake.length; i++) {
      const s = snake[i];
      const t = i / Math.max(1, snake.length - 1);
      ctx.globalAlpha = 0.22 + (1 - t) * 0.28; // tête plus visible
      const pad = i === 0 ? 2 : 3;
      const x = s.x * cell + ox + pad;
      const y = s.y * cell + oy + pad;
      const size = cell - pad * 2;
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(x, y, size, size);
    }
    ctx.globalAlpha = 1;
  }

  function loop(ts) {
    if (!last) last = ts;
    if (ts - last >= STEP_MS) {
      step();
      last = ts;
      tick++;
    }
    draw();
    requestAnimationFrame(loop);
  }

  window.addEventListener("resize", resize);
  resize();
  requestAnimationFrame(loop);
})();
