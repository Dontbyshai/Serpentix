/**
 * dessin.js — Fonctions de dessin du plateau, PARTAGÉES par le solo et le multijoueur.
 *
 * Idée NSI « réutiliser du code » : le solo (solo.js) et les parties à 2 ou 3
 * (game.js) appellent la même fonction Dessin.plateau(), donc le jeu a
 * exactement le même aspect dans les deux modes et on ne corrige un bug qu'une fois.
 *
 * Contrainte de style : uniquement du noir (#000) et du blanc (#fff), aucune
 * transparence (qui donnerait du gris). Seuls les serpents ont une couleur.
 * Les bonus sont des pictogrammes au trait blanc (pas d'emoji en couleur).
 */
const Dessin = (function () {
  const NOIR = "#000000";
  const BLANC = "#ffffff";

  /**
   * Dessine un rectangle aux coins arrondis (le chemin seulement).
   * @param {CanvasRenderingContext2D} ctx - contexte 2D du canvas
   * @param {number} x - abscisse du coin haut-gauche (pixels)
   * @param {number} y - ordonnée du coin haut-gauche (pixels)
   * @param {number} w - largeur
   * @param {number} h - hauteur
   * @param {number} r - rayon des coins
   */
  function rectArrondi(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  /**
   * Dessine le pictogramme d'un bonus, centré en (x, y), au trait blanc.
   * Un dessin différent par type pour les reconnaître d'un coup d'œil :
   *   turbo = triangle, bouclier = cercle, fantôme = carré en pointillés,
   *   aimant = fer à cheval (U), ciseaux = croix à deux anneaux, gel = flocon.
   * @param {CanvasRenderingContext2D} ctx
   * @param {string} type - clé du bonus
   * @param {number} x - centre (pixels)
   * @param {number} y - centre (pixels)
   * @param {number} r - « rayon » du pictogramme
   */
  function pictogramme(ctx, type, x, y, r) {
    ctx.save();
    ctx.strokeStyle = BLANC;
    ctx.fillStyle = BLANC;
    ctx.lineWidth = Math.max(1.5, r * 0.22);
    ctx.lineCap = "round";
    ctx.beginPath();
    if (type === "turbo") {
      ctx.moveTo(x, y - r);
      ctx.lineTo(x + r, y + r * 0.85);
      ctx.lineTo(x - r, y + r * 0.85);
      ctx.closePath();
      ctx.stroke();
    } else if (type === "bouclier") {
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(x, y, r * 0.3, 0, Math.PI * 2);
      ctx.fill();
    } else if (type === "fantome") {
      ctx.setLineDash([r * 0.35, r * 0.3]);
      ctx.strokeRect(x - r, y - r, r * 2, r * 2);
    } else if (type === "aimant") {
      // Fer à cheval : demi-cercle en bas + deux branches vers le haut
      ctx.arc(x, y, r * 0.75, 0, Math.PI);
      ctx.moveTo(x - r * 0.75, y);
      ctx.lineTo(x - r * 0.75, y - r);
      ctx.moveTo(x + r * 0.75, y);
      ctx.lineTo(x + r * 0.75, y - r);
      ctx.stroke();
    } else if (type === "ciseaux") {
      // Deux lames croisées + deux anneaux
      ctx.moveTo(x - r, y - r);
      ctx.lineTo(x + r * 0.4, y + r * 0.25);
      ctx.moveTo(x + r, y - r);
      ctx.lineTo(x - r * 0.4, y + r * 0.25);
      ctx.stroke();
      [-1, 1].forEach(function (c) {
        ctx.beginPath();
        ctx.arc(x + c * r * 0.5, y + r * 0.6, r * 0.32, 0, Math.PI * 2);
        ctx.stroke();
      });
    } else if (type === "gel") {
      // Flocon : 3 traits qui se croisent (6 branches)
      for (let k = 0; k < 3; k++) {
        const a = (k * Math.PI) / 3 + Math.PI / 2;
        ctx.moveTo(x + Math.cos(a) * r, y + Math.sin(a) * r);
        ctx.lineTo(x - Math.cos(a) * r, y - Math.sin(a) * r);
      }
      ctx.stroke();
    }
    ctx.restore();
  }

  /**
   * Crée un petit <canvas> contenant le pictogramme d'un bonus.
   * Utilisé par le HUD et la légende : même dessin que sur le plateau.
   * @param {string} type
   * @param {number} [taille=18] - côté en pixels
   * @returns {HTMLCanvasElement}
   */
  function icone(type, taille) {
    taille = taille || 18;
    const c = document.createElement("canvas");
    c.width = taille;
    c.height = taille;
    c.className = "picto";
    pictogramme(c.getContext("2d"), type, taille / 2, taille / 2, taille * 0.36);
    return c;
  }

  /**
   * Dessine un serpent case par case.
   * @param {CanvasRenderingContext2D} ctx
   * @param {Object} s - serpent {corps, couleur, vivant, bouclier, fantome, gele}
   * @param {number} cw - largeur d'une case en pixels
   * @param {number} ch - hauteur d'une case en pixels
   */
  function serpent(ctx, s, cw, ch) {
    const corps = s.corps || [];
    for (let i = corps.length - 1; i >= 0; i--) {   // de la queue vers la tête
      const px = corps[i][0] * cw;
      const py = corps[i][1] * ch;
      const pad = i === 0 ? 1 : 2;                   // la tête est un peu plus grosse
      rectArrondi(ctx, px + pad, py + pad, cw - pad * 2, ch - pad * 2, 4);
      if (!s.vivant) {
        // Serpent éliminé : seulement un contour fin (pas de gris translucide)
        ctx.strokeStyle = s.couleur;
        ctx.lineWidth = 1;
        ctx.stroke();
      } else if (s.fantome) {
        // Fantôme : contour en pointillés de la couleur du skin (« intangible »)
        ctx.save();
        ctx.setLineDash([3, 3]);
        ctx.strokeStyle = s.couleur;
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.restore();
      } else {
        ctx.fillStyle = s.couleur;
        ctx.fill();
        if (s.gele && i % 2 === 0) {
          // Gelé : un petit point noir sur une case sur deux (effet « givre »)
          ctx.fillStyle = NOIR;
          ctx.fillRect(px + cw / 2 - 1.5, py + ch / 2 - 1.5, 3, 3);
        }
      }
    }
    if (!corps.length) return;
    const tete = corps[0];
    const cx = tete[0] * cw + cw / 2;
    const cy = tete[1] * ch + ch / 2;
    if (!s.vivant) {
      // Croix sur la tête d'un serpent éliminé
      ctx.strokeStyle = s.couleur;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(cx - cw * 0.3, cy - ch * 0.3);
      ctx.lineTo(cx + cw * 0.3, cy + ch * 0.3);
      ctx.moveTo(cx + cw * 0.3, cy - ch * 0.3);
      ctx.lineTo(cx - cw * 0.3, cy + ch * 0.3);
      ctx.stroke();
      return;
    }

    // Yeux sur la tête, placés du côté où le serpent regarde
    const cou = corps[1] || [tete[0] - 1, tete[1]];
    const dx = tete[0] - cou[0];
    const dy = tete[1] - cou[1];
    ctx.fillStyle = s.fantome ? s.couleur : NOIR;
    [-1, 1].forEach(function (cote) {
      // perpendiculaire à la direction (-dy, dx) pour écarter les deux yeux
      const ex = cx + dx * cw * 0.18 + -dy * cote * cw * 0.2;
      const ey = cy + dy * ch * 0.18 + dx * cote * ch * 0.2;
      ctx.beginPath();
      ctx.arc(ex, ey, Math.max(1.5, cw * 0.09), 0, Math.PI * 2);
      ctx.fill();
    });

    // Bouclier = anneau blanc autour de la tête
    if (s.bouclier) {
      ctx.strokeStyle = BLANC;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx, cy, Math.max(cw, ch) * 0.75, 0, Math.PI * 2);
      ctx.stroke();
    }
  }

  /**
   * Dessine tout le plateau à partir d'un état.
   * @param {HTMLCanvasElement} canvas
   * @param {Object} etat - {largeur, hauteur, pommes, bonus, serpents}
   */
  function plateau(canvas, etat) {
    const ctx = canvas.getContext("2d");
    const W = canvas.width;
    const H = canvas.height;
    const cw = W / etat.largeur;
    const ch = H / etat.hauteur;

    // Fond noir + petite grille de points blancs (1 point toutes les 2 cases)
    ctx.fillStyle = NOIR;
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = BLANC;
    for (let y = 2; y < etat.hauteur; y += 2) {
      for (let x = 2; x < etat.largeur; x += 2) {
        ctx.fillRect(Math.round(x * cw) - 1, Math.round(y * ch) - 1, 2, 2);
      }
    }

    // Pommes : disques blancs
    (etat.pommes || []).forEach(function (p) {
      ctx.beginPath();
      ctx.fillStyle = BLANC;
      ctx.arc(p[0] * cw + cw / 2, p[1] * ch + ch / 2, Math.min(cw, ch) * 0.32, 0, Math.PI * 2);
      ctx.fill();
    });

    // Bonus : pictogrammes blancs (voir pictogramme())
    (etat.bonus || []).forEach(function (b) {
      pictogramme(ctx, b.type, b.pos[0] * cw + cw / 2, b.pos[1] * ch + ch / 2,
        Math.min(cw, ch) * 0.4);
    });

    // Les serpents éliminés d'abord (en dessous), les vivants par-dessus
    const serpents = etat.serpents || [];
    serpents.filter(function (s) { return !s.vivant; }).forEach(function (s) { serpent(ctx, s, cw, ch); });
    serpents.filter(function (s) { return s.vivant; }).forEach(function (s) { serpent(ctx, s, cw, ch); });
  }

  /**
   * Affiche un grand texte centré (compte à rebours, code de salle, pause…).
   * @param {HTMLCanvasElement} canvas
   * @param {string} texte
   */
  function texteCentre(canvas, texte) {
    const ctx = canvas.getContext("2d");
    const taille = Math.round(canvas.height / 5);
    ctx.font = "700 " + taille + "px 'Space Grotesk', system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const largeur = ctx.measureText(texte).width + taille;
    // Cadre noir bordé de blanc pour rester lisible au-dessus du jeu
    ctx.fillStyle = NOIR;
    ctx.fillRect(canvas.width / 2 - largeur / 2, canvas.height / 2 - taille * 0.75, largeur, taille * 1.5);
    ctx.strokeStyle = BLANC;
    ctx.lineWidth = 2;
    ctx.strokeRect(canvas.width / 2 - largeur / 2, canvas.height / 2 - taille * 0.75, largeur, taille * 1.5);
    ctx.fillStyle = BLANC;
    ctx.fillText(texte, canvas.width / 2, canvas.height / 2 + 2);
  }

  /**
   * Remplit un élément HTML avec les effets actifs d'un serpent : pictogramme
   * + secondes restantes + petite barre qui se vide. Construit avec
   * createElement/textContent (jamais innerHTML) : aucune injection possible.
   * @param {HTMLElement} el - conteneur à remplir
   * @param {Object} s - serpent {effets: {turbo: 2.1, ...}, bouclier}
   * @param {Object} durees - durée totale de chaque effet en secondes
   */
  function effetsHUD(el, s, durees) {
    el.textContent = "";
    const effets = Object.assign({}, s.effets || {});
    if (s.bouclier) effets.bouclier = null;          // le bouclier n'a pas de minuteur
    Object.keys(effets).forEach(function (nom) {
      const puce = document.createElement("span");
      puce.className = "effet";
      puce.appendChild(icone(nom, 16));
      const t = document.createElement("span");
      t.textContent = effets[nom] === null ? "prêt" : effets[nom].toFixed(1) + " s";
      puce.appendChild(t);
      if (effets[nom] !== null && durees && durees[nom]) {
        // Barre de progression : largeur proportionnelle au temps restant
        const barre = document.createElement("span");
        barre.className = "effet-barre";
        const plein = document.createElement("span");
        plein.style.width = Math.max(0, Math.min(100, (100 * effets[nom]) / durees[nom])) + "%";
        barre.appendChild(plein);
        puce.appendChild(barre);
      }
      el.appendChild(puce);
    });
  }

  // Seules ces fonctions sont « publiques » (module JavaScript simple)
  return { plateau: plateau, texteCentre: texteCentre, icone: icone, effetsHUD: effetsHUD };
})();

// Légendes des bonus dans les pages : <span data-picto="turbo"></span> reçoit
// automatiquement le même pictogramme que sur le plateau.
document.querySelectorAll("[data-picto]").forEach(function (el) {
  el.appendChild(Dessin.icone(el.dataset.picto, 20));
});
