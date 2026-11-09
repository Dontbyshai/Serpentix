/**
 * fin.js — Écrans de fin animés (victoire, défaite, match nul), PARTAGÉS
 * par le solo et le multijoueur.
 *
 * - Le grand titre est animé en CSS (classes .fin-victoire, .fin-defaite,
 *   .fin-nul dans style.css).
 * - Les particules sont dessinées dans un <canvas> plein écran avec
 *   requestAnimationFrame (≈ 60 images/s, s'arrête tout seul après 4 s).
 * - Couleurs : noir et blanc uniquement, SAUF la couleur du skin du
 *   vainqueur, autorisée dans les confettis de victoire.
 *
 * Utilisation : Fin.afficher({type: "victoire", titre: "VICTOIRE",
 *                             message: "...", couleur: "#ef4444"});
 */
const Fin = (function () {
  const DUREE_MS = 4000;      // durée de l'animation des particules
  let animation = null;       // identifiant requestAnimationFrame en cours

  /**
   * Crée la liste des particules selon le type d'écran.
   * @param {string} type - "victoire" | "defaite" | "nul"
   * @param {number} W - largeur de l'écran (pixels)
   * @param {number} H - hauteur
   * @param {string} couleur - couleur du skin du vainqueur
   * @returns {Array<Object>} particules {x, y, vx, vy, taille, couleur, rot, vrot}
   */
  function creerParticules(type, W, H, couleur) {
    const liste = [];
    const couleurs = ["#ffffff"];
    if (type === "victoire" && couleur && couleur.toLowerCase() !== "#ffffff") {
      couleurs.push(couleur, couleur);          // 2 confettis sur 3 à la couleur du skin
    }
    if (type === "victoire") {
      // Explosion depuis le centre + pluie de confettis depuis le haut
      for (let i = 0; i < 160; i++) {
        const angle = Math.random() * Math.PI * 2;
        const vitesse = 4 + Math.random() * 9;
        liste.push({
          x: W / 2, y: H / 2,
          vx: Math.cos(angle) * vitesse, vy: Math.sin(angle) * vitesse - 3,
          taille: 4 + Math.random() * 7, couleur: couleurs[i % couleurs.length],
          rot: Math.random() * 6, vrot: (Math.random() - 0.5) * 0.4, gravite: 0.18,
        });
      }
      for (let i = 0; i < 90; i++) {
        liste.push({
          x: Math.random() * W, y: -Math.random() * H * 0.6,
          vx: (Math.random() - 0.5) * 1.5, vy: 2 + Math.random() * 3,
          taille: 5 + Math.random() * 6, couleur: couleurs[i % couleurs.length],
          rot: Math.random() * 6, vrot: (Math.random() - 0.5) * 0.3, gravite: 0.03,
        });
      }
    } else if (type === "defaite") {
      // Le titre « se brise » : petits carrés blancs qui tombent lentement
      for (let i = 0; i < 70; i++) {
        liste.push({
          x: W / 2 + (Math.random() - 0.5) * 360, y: H / 2 + (Math.random() - 0.5) * 60,
          vx: (Math.random() - 0.5) * 1.2, vy: Math.random() * 1.5,
          taille: 2 + Math.random() * 4, couleur: "#ffffff",
          rot: 0, vrot: 0, gravite: 0.06,
        });
      }
    } else {
      // Match nul : deux gerbes symétriques qui se rencontrent au centre
      for (let i = 0; i < 120; i++) {
        const cote = i % 2 === 0 ? -1 : 1;
        liste.push({
          x: cote < 0 ? 0 : W, y: H / 2 + (Math.random() - 0.5) * 120,
          vx: -cote * (5 + Math.random() * 6), vy: (Math.random() - 0.5) * 3,
          taille: 3 + Math.random() * 5, couleur: "#ffffff",
          rot: Math.random() * 6, vrot: (Math.random() - 0.5) * 0.3, gravite: 0.05,
        });
      }
    }
    return liste;
  }

  /**
   * Lance l'animation des particules dans le canvas plein écran.
   * @param {HTMLCanvasElement} canvas
   * @param {string} type
   * @param {string} couleur
   */
  function animer(canvas, type, couleur) {
    if (animation) cancelAnimationFrame(animation);
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    const ctx = canvas.getContext("2d");
    const particules = creerParticules(type, canvas.width, canvas.height, couleur);
    const debut = performance.now();

    function image(maintenant) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);   // fond transparent : le plateau reste visible
      particules.forEach(function (p) {
        p.vy += p.gravite;           // la gravité accélère la chute
        p.vx *= 0.99;                // frottement de l'air
        p.x += p.vx;
        p.y += p.vy;
        p.rot += p.vrot;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot);
        ctx.fillStyle = p.couleur;
        ctx.fillRect(-p.taille / 2, -p.taille / 2, p.taille, p.taille * 0.6);
        ctx.restore();
      });
      if (maintenant - debut < DUREE_MS) {
        animation = requestAnimationFrame(image);
      } else {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        animation = null;
      }
    }
    animation = requestAnimationFrame(image);
  }

  /**
   * Affiche l'écran de fin.
   * @param {Object} o - {type, titre, message, couleur}
   */
  function afficher(o) {
    const overlay = document.getElementById("fin-overlay");
    const titre = document.getElementById("fin-titre");
    const msg = document.getElementById("fin-msg");
    const fx = document.getElementById("fin-fx");
    if (!overlay) return;
    overlay.classList.remove("hidden", "fin-victoire", "fin-defaite", "fin-nul");
    // Forcer le navigateur à « oublier » l'ancienne animation CSS pour la rejouer
    void overlay.offsetWidth;
    overlay.classList.add("fin-" + o.type);
    titre.textContent = o.titre;
    // Le titre d'une victoire prend la couleur du skin (seule couleur permise)
    titre.style.color = o.type === "victoire" && o.couleur ? o.couleur : "";
    msg.textContent = o.message || "";
    if (fx) animer(fx, o.type, o.couleur);
    if (typeof Controles !== "undefined") Controles.deverrouiller();   // la page redevient normale
  }

  /** Cache l'écran de fin (bouton « Rejouer » du solo). */
  function cacher() {
    const overlay = document.getElementById("fin-overlay");
    if (overlay) overlay.classList.add("hidden");
    if (animation) cancelAnimationFrame(animation);
    animation = null;
  }

  return { afficher: afficher, cacher: cacher };
})();
