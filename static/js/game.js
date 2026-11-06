/**
 * game.js — Client du jeu 1v1 (canvas + Socket.IO)
 * Plateau noir & blanc ; seules les couleurs de skins colorent les serpents.
 */
(function () {
  const canvas = document.getElementById("game");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const statusEl = document.getElementById("game-status");
  const scoresEl = document.getElementById("scores");
  const overlay = document.getElementById("fin-overlay");
  const finMsg = document.getElementById("fin-msg");
  const code = window.SERPENTIX_CODE;

  const socket = io({ transports: ["websocket", "polling"] });

  socket.on("connect", function () {
    statusEl.textContent = "Connecté — salle " + code;
    socket.emit("rejoindre_salle", { code: code });
  });

  socket.on("erreur", function (data) {
    statusEl.textContent = data.message || "Erreur";
  });

  socket.on("partie_lancee", function () {
    statusEl.textContent = "Partie en cours !";
  });

  socket.on("etat_jeu", function (data) {
    if (data.statut === "attente") {
      statusEl.textContent = "En attente… (" + data.nb_joueurs + "/2) — partage le code " + data.code;
    } else if (data.statut === "en_cours") {
      statusEl.textContent = "En cours";
    } else if (data.statut === "terminee") {
      statusEl.textContent = "Terminée";
      finMsg.textContent = data.message_fin || "Fin de partie";
      overlay.classList.remove("hidden");
    }
    renderScores(data);
    dessiner(data);
  });

  function renderScores(data) {
    if (!scoresEl) return;
    scoresEl.innerHTML = "";
    (data.serpents || []).forEach(function (s) {
      const pill = document.createElement("div");
      pill.className = "score-pill";
      pill.innerHTML =
        '<span class="swatch" style="background:' + s.couleur + '"></span>' +
        "<strong>" + s.pseudo + "</strong> " + s.score +
        (s.bouclier ? " ○" : "") +
        (s.turbo ? " △" : "") +
        (s.vivant ? "" : " ×");
      scoresEl.appendChild(pill);
    });
  }

  function dessiner(data) {
    const W = canvas.width;
    const H = canvas.height;
    const cw = W / data.largeur;
    const ch = H / data.hauteur;

    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, W, H);
    for (let y = 0; y < data.hauteur; y++) {
      for (let x = 0; x < data.largeur; x++) {
        if ((x + y) % 2 === 0) {
          ctx.fillStyle = "#0a0a0a";
          ctx.fillRect(x * cw, y * ch, cw, ch);
        }
      }
    }

    (data.pommes || []).forEach(function (p) {
      const x = p[0] * cw + cw / 2;
      const y = p[1] * ch + ch / 2;
      ctx.beginPath();
      ctx.fillStyle = "#ffffff";
      ctx.arc(x, y, Math.min(cw, ch) * 0.32, 0, Math.PI * 2);
      ctx.fill();
    });

    (data.bonus || []).forEach(function (b) {
      const x = b.pos[0] * cw + cw / 2;
      const y = b.pos[1] * ch + ch / 2;
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
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

    (data.serpents || []).forEach(function (s) {
      const corps = s.corps || [];
      corps.forEach(function (seg, i) {
        const px = seg[0] * cw;
        const py = seg[1] * ch;
        ctx.fillStyle = s.couleur;
        ctx.globalAlpha = s.vivant ? (i === 0 ? 1 : 0.85) : 0.3;
        const pad = i === 0 ? 1 : 2;
        roundRect(ctx, px + pad, py + pad, cw - pad * 2, ch - pad * 2, 4);
        ctx.fill();
        if (i === 0 && s.bouclier) {
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = 2;
          ctx.strokeRect(px + 1, py + 1, cw - 2, ch - 2);
        }
      });
      ctx.globalAlpha = 1;
    });
  }

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  const dirs = {
    ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0],
    w: [0, -1], s: [0, 1], a: [-1, 0], d: [1, 0],
    W: [0, -1], S: [0, 1], A: [-1, 0], D: [1, 0],
  };
  window.addEventListener("keydown", function (ev) {
    const d = dirs[ev.key];
    if (!d) return;
    ev.preventDefault();
    socket.emit("direction", { code: code, dx: d[0], dy: d[1] });
  });

  window.addEventListener("beforeunload", function () {
    socket.emit("quitter_salle", { code: code });
  });
})();
