/**
 * solo.js — Mode entraînement client + crédit de coins en fin de partie
 */
(function () {
  const canvas = document.getElementById("solo-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const scoreEl = document.getElementById("solo-score");
  const gainEl = document.getElementById("solo-gain");
  const btn = document.getElementById("solo-restart");
  const again = document.getElementById("solo-again");
  const overlay = document.getElementById("fin-overlay");
  const finMsg = document.getElementById("fin-msg");
  const SKIN = window.SERPENTIX_SKIN || "#ffffff";

  const COLS = 40, ROWS = 30;
  const cw = canvas.width / COLS, ch = canvas.height / ROWS;

  let serpent, dir, nextDir, pommes, bonus, score, vivant, bouclier, turbo, grandir, timer;
  let coinsEnvoyes = false;

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
    coinsEnvoyes = false;
    if (overlay) overlay.classList.add("hidden");
    spawnPommes();
    spawnBonus();
    scoreEl.textContent = "0";
    if (gainEl) gainEl.textContent = "0";
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

  async function crediterCoins() {
    if (coinsEnvoyes) return;
    coinsEnvoyes = true;
    try {
      const res = await fetch("/api/solo/fin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ score: score }),
      });
      const data = await res.json();
      if (data.ok) {
        if (gainEl) gainEl.textContent = String(data.gain);
        if (finMsg) {
          finMsg.textContent = "Score " + score + " · +" + data.gain + " coins (solde " + data.coins + ")";
        }
      }
    } catch (e) {
      if (finMsg) finMsg.textContent = "Score " + score + " (coins non crédités — réseau)";
    }
  }

  function gameOver() {
    vivant = false;
    if (overlay) overlay.classList.remove("hidden");
    if (finMsg) finMsg.textContent = "Score " + score + "…";
    crediterCoins();
    draw();
  }

  function tick() {
    if (!vivant) return;
    dir = nextDir;
    const steps = turbo > 0 ? 2 : 1;
    if (turbo > 0) turbo--;
    for (let s = 0; s < steps; s++) {
      const head = [serpent[0][0] + dir[0], serpent[0][1] + dir[1]];
      const mur = head[0] < 0 || head[1] < 0 || head[0] >= COLS || head[1] >= ROWS;
      const soi = serpent.some(function (p) { return p[0] === head[0] && p[1] === head[1]; });
      if (mur || soi) {
        if (bouclier) {
          bouclier = false;
          break;
        }
        gameOver();
        return;
      }
      serpent.unshift(head);
      if (grandir > 0) grandir--;
      else serpent.pop();

      for (let i = 0; i < pommes.length; i++) {
        if (pommes[i][0] === head[0] && pommes[i][1] === head[1]) {
          pommes.splice(i, 1);
          score++;
          grandir++;
          scoreEl.textContent = String(score);
          if (gainEl) gainEl.textContent = String(Math.min(score, 80));
          break;
        }
      }
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
    // Plateau noir & blanc uniquement
    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    for (let y = 0; y < ROWS; y++) {
      for (let x = 0; x < COLS; x++) {
        if ((x + y) % 2 === 0) {
          ctx.fillStyle = "#0a0a0a";
          ctx.fillRect(x * cw, y * ch, cw, ch);
        }
      }
    }
    // Pommes = cercles blancs (pas de couleur UI)
    pommes.forEach(function (p) {
      ctx.beginPath();
      ctx.fillStyle = "#ffffff";
      ctx.arc(p[0] * cw + cw / 2, p[1] * ch + ch / 2, Math.min(cw, ch) * 0.32, 0, Math.PI * 2);
      ctx.fill();
    });
    bonus.forEach(function (b) {
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      const x = b.pos[0] * cw + cw / 2;
      const y = b.pos[1] * ch + ch / 2;
      if (b.type === "turbo") {
        ctx.beginPath();
        ctx.moveTo(x, y - 7);
        ctx.lineTo(x + 6, y + 6);
        ctx.lineTo(x - 6, y + 6);
        ctx.closePath();
        ctx.stroke();
      } else {
        ctx.beginPath();
        ctx.arc(x, y, 7, 0, Math.PI * 2);
        ctx.stroke();
      }
    });
    serpent.forEach(function (seg, i) {
      ctx.globalAlpha = vivant ? 1 : 0.35;
      ctx.fillStyle = SKIN;
      const pad = i === 0 ? 1 : 2;
      ctx.fillRect(seg[0] * cw + pad, seg[1] * ch + pad, cw - pad * 2, ch - pad * 2);
      if (i === 0 && bouclier) {
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.strokeRect(seg[0] * cw + 1, seg[1] * ch + 1, cw - 2, ch - 2);
      }
    });
    ctx.globalAlpha = 1;
  }

  const map = {
    ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0],
    w: [0, -1], s: [0, 1], a: [-1, 0], d: [1, 0],
    W: [0, -1], S: [0, 1], A: [-1, 0], D: [1, 0],
  };
  window.addEventListener("keydown", function (ev) {
    const d = map[ev.key];
    if (!d) return;
    if (d[0] === -dir[0] && d[1] === -dir[1]) return;
    ev.preventDefault();
    nextDir = d;
  });

  if (btn) btn.addEventListener("click", reset);
  if (again) again.addEventListener("click", reset);
  reset();
})();
