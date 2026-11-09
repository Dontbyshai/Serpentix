/**
 * solo.js — Mode entraînement 100 % client (pas de Socket.IO)
 * Sert à tester les contrôles avant un vrai 1v1.
 */
(function () {
  const canvas = document.getElementById("solo-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const scoreEl = document.getElementById("solo-score");
  const btn = document.getElementById("solo-restart");

  const COLS = 40, ROWS = 30;
  const cw = canvas.width / COLS, ch = canvas.height / ROWS;

  let serpent, dir, nextDir, pommes, bonus, score, vivant, bouclier, turbo, grandir, timer;

  function reset() {
    serpent = [[8, 15], [7, 15], [6, 15]];
    dir = [1, 0];
    nextDir = [1, 0];
    score = 0;
    vivant = true;
    bouclier = false;
    turbo = 0;
    grandir = 0;
    pommes = [];
    bonus = [];
    spawnPommes();
    spawnBonus();
    scoreEl.textContent = "0";
    if (timer) clearInterval(timer);
    timer = setInterval(tick, 100);
    draw();
  }

  function occupees() {
    const s = new Set(serpent.map(function (p) { return p[0] + "," + p[1]; }));
    pommes.forEach(function (p) { s.add(p[0] + "," + p[1]); });
    bonus.forEach(function (b) { s.add(b.pos[0] + "," + b.pos[1]); });
    return s;
  }

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

  function spawnPommes() {
    while (pommes.length < 3) {
      const c = caseLibre();
      if (!c) break;
      pommes.push(c);
    }
  }

  function spawnBonus() {
    while (bonus.length < 2) {
      const c = caseLibre();
      if (!c) break;
      bonus.push({ pos: c, type: Math.random() < 0.5 ? "turbo" : "bouclier" });
    }
  }

  function tick() {
    if (!vivant) return;
    dir = nextDir;
    const steps = turbo > 0 ? 2 : 1;
    if (turbo > 0) turbo--;
    for (let s = 0; s < steps; s++) {
      const head = [serpent[0][0] + dir[0], serpent[0][1] + dir[1]];
      // Mur ou soi
      const mur = head[0] < 0 || head[1] < 0 || head[0] >= COLS || head[1] >= ROWS;
      const soi = serpent.some(function (p) { return p[0] === head[0] && p[1] === head[1]; });
      if (mur || soi) {
        if (bouclier) {
          bouclier = false;
          break;
        }
        vivant = false;
        draw();
        return;
      }
      serpent.unshift(head);
      if (grandir > 0) grandir--;
      else serpent.pop();

      // Pomme
      for (let i = 0; i < pommes.length; i++) {
        if (pommes[i][0] === head[0] && pommes[i][1] === head[1]) {
          pommes.splice(i, 1);
          score++;
          grandir++;
          scoreEl.textContent = String(score);
          break;
        }
      }
      // Bonus
      for (let i = 0; i < bonus.length; i++) {
        if (bonus[i].pos[0] === head[0] && bonus[i].pos[1] === head[1]) {
          if (bonus[i].type === "turbo") turbo = 40;
          else bouclier = true;
          bonus.splice(i, 1);
          break;
        }
      }
    }
    spawnPommes();
    if (Math.random() < 0.02) spawnBonus();
    draw();
  }

  function draw() {
    ctx.fillStyle = "#060a12";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    for (let y = 0; y < ROWS; y++) {
      for (let x = 0; x < COLS; x++) {
        if ((x + y) % 2 === 0) {
          ctx.fillStyle = "#0a1220";
          ctx.fillRect(x * cw, y * ch, cw, ch);
        }
      }
    }
    pommes.forEach(function (p) {
      ctx.beginPath();
      ctx.fillStyle = "#ef4444";
      ctx.arc(p[0] * cw + cw / 2, p[1] * ch + ch / 2, Math.min(cw, ch) * 0.35, 0, Math.PI * 2);
      ctx.fill();
    });
    bonus.forEach(function (b) {
      ctx.font = Math.floor(Math.min(cw, ch) * 0.7) + "px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(b.type === "turbo" ? "⚡" : "🛡️", b.pos[0] * cw + cw / 2, b.pos[1] * ch + ch / 2);
    });
    serpent.forEach(function (seg, i) {
      ctx.globalAlpha = vivant ? 1 : 0.4;
      ctx.fillStyle = "#22c55e";
      ctx.fillRect(seg[0] * cw + 1, seg[1] * ch + 1, cw - 2, ch - 2);
      if (i === 0 && bouclier) {
        ctx.strokeStyle = "#38bdf8";
        ctx.strokeRect(seg[0] * cw + 1, seg[1] * ch + 1, cw - 2, ch - 2);
      }
    });
    ctx.globalAlpha = 1;
    if (!vivant) {
      ctx.fillStyle = "#ffffffcc";
      ctx.font = "bold 28px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Game Over — score " + score, canvas.width / 2, canvas.height / 2);
    }
  }

  const map = {
    ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0],
    w: [0, -1], s: [0, 1], a: [-1, 0], d: [1, 0],
    W: [0, -1], S: [0, 1], A: [-1, 0], D: [1, 0],
  };
  window.addEventListener("keydown", function (ev) {
    const d = map[ev.key];
    if (!d) return;
    // Pas de demi-tour
    if (d[0] === -dir[0] && d[1] === -dir[1]) return;
    ev.preventDefault();
    nextDir = d;
  });

  if (btn) btn.addEventListener("click", reset);
  reset();
})();
