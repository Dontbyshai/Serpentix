/**
 * dessin.js — Fonctions de dessin du plateau, PARTAGÉES par le solo et le 1v1.
 *
 * Idée NSI « réutiliser du code » : le solo (solo.js) et le 1v1 (game.js)
 * appellent la même fonction Dessin.plateau(), donc le jeu a exactement le
 * même aspect dans les deux modes et on ne corrige un bug qu'une fois.
 *
 * Contrainte de style : uniquement du noir (#000) et du blanc (#fff), aucune
 * transparence (qui donnerait du gris). Seuls les serpents ont une couleur.
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
   * Dessine un serpent case par case.
   * @param {CanvasRenderingContext2D} ctx
   * @param {Object} s - serpent {corps: [[x,y],...], couleur, vivant, bouclier, turbo}
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
      if (s.vivant) {
        ctx.fillStyle = s.couleur;
        ctx.fill();
      } else {
        // Serpent éliminé : seulement le contour (pas de gris translucide)
        ctx.strokeStyle = s.couleur;
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }
    if (!corps.length || !s.vivant) return;

    // Yeux noirs sur la tête, placés du côté où le serpent regarde
    const tete = corps[0];
    const cou = corps[1] || [tete[0] - 1, tete[1]];
    const dx = tete[0] - cou[0];
    const dy = tete[1] - cou[1];
    const cx = tete[0] * cw + cw / 2;
    const cy = tete[1] * ch + ch / 2;
    ctx.fillStyle = NOIR;
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

    // Bonus : triangle = turbo, cercle = bouclier (contours blancs)
    (etat.bonus || []).forEach(function (b) {
      const x = b.pos[0] * cw + cw / 2;
      const y = b.pos[1] * ch + ch / 2;
      const r = Math.min(cw, ch) * 0.38;
      ctx.strokeStyle = BLANC;
      ctx.lineWidth = 2;
      ctx.beginPath();
      if (b.type === "turbo") {
        ctx.moveTo(x, y - r);
        ctx.lineTo(x + r, y + r);
        ctx.lineTo(x - r, y + r);
        ctx.closePath();
      } else {
        ctx.arc(x, y, r, 0, Math.PI * 2);
      }
      ctx.stroke();
    });

    (etat.serpents || []).forEach(function (s) { serpent(ctx, s, cw, ch); });
  }

  /**
   * Affiche un grand texte centré (compte à rebours, « GO », pause…).
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

  // Seules ces fonctions sont « publiques » (module JavaScript simple)
  return { plateau: plateau, texteCentre: texteCentre };
})();
