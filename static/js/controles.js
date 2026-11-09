/**
 * controles.js — Contrôles du serpent, PARTAGÉS par le solo et le multijoueur.
 *
 * Trois façons de diriger le serpent :
 *   1) clavier : flèches ou ZQSD / WASD ;
 *   2) glisser le doigt sur le plateau (téléphone, tablette) ;
 *   3) boutons fléchés à l'écran (élément .dpad, visible sur mobile).
 * Chaque action appelle la même fonction rappel(dx, dy).
 *
 * Ce fichier gère aussi le « verrou de défilement » : pendant une partie, la
 * page ne doit JAMAIS bouger (molette, doigt, flèches, espace), sinon le
 * plateau glisse hors de l'écran au mauvais moment.
 */
const Controles = (function () {
  // Table de correspondance touche → vecteur [dx, dy] (y vers le bas)
  const TOUCHES = {
    ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0],
    z: [0, -1], q: [-1, 0],             // clavier AZERTY (ZQSD)
    w: [0, -1], a: [-1, 0],             // clavier QWERTY (WASD)
    s: [0, 1], d: [1, 0],
  };
  const SEUIL_GLISSER = 20;              // pixels minimum pour compter un glissement

  /**
   * Branche les trois types de contrôles.
   * @param {HTMLCanvasElement} canvas - plateau (pour le glisser)
   * @param {function(number, number): void} rappel - appelée avec (dx, dy)
   */
  function brancher(canvas, rappel) {
    // 1) Clavier
    window.addEventListener("keydown", function (ev) {
      const d = TOUCHES[ev.key] || TOUCHES[ev.key.toLowerCase()];
      if (!d) return;
      ev.preventDefault();               // empêche les flèches de faire défiler la page
      rappel(d[0], d[1]);
    });
    // Pas de sélection de texte ni de « glisser l'image » sur le plateau
    canvas.addEventListener("dragstart", function (ev) { ev.preventDefault(); });
    canvas.addEventListener("selectstart", function (ev) { ev.preventDefault(); });

    // 2) Glisser le doigt : on compare le point de départ et d'arrivée
    let depart = null;
    canvas.addEventListener("touchstart", function (ev) {
      const t = ev.changedTouches[0];
      depart = { x: t.clientX, y: t.clientY };
    }, { passive: true });
    canvas.addEventListener("touchmove", function (ev) {
      if (!depart) return;
      const t = ev.changedTouches[0];
      const dx = t.clientX - depart.x;
      const dy = t.clientY - depart.y;
      if (Math.max(Math.abs(dx), Math.abs(dy)) < SEUIL_GLISSER) return;
      // Le plus grand déplacement l'emporte : horizontal ou vertical
      if (Math.abs(dx) > Math.abs(dy)) rappel(dx > 0 ? 1 : -1, 0);
      else rappel(0, dy > 0 ? 1 : -1);
      depart = { x: t.clientX, y: t.clientY }; // permet d'enchaîner les virages
    }, { passive: true });
    canvas.addEventListener("touchend", function () { depart = null; });

    // 3) Boutons fléchés : <button data-dir="0,-1">
    document.querySelectorAll(".dpad [data-dir]").forEach(function (bouton) {
      bouton.addEventListener("pointerdown", function (ev) {
        ev.preventDefault();
        const v = bouton.dataset.dir.split(",").map(Number);
        rappel(v[0], v[1]);
      });
    });
  }

  // --- Verrou de défilement ----------------------------------------------
  // Touches qui font défiler une page : flèches, espace, Page haut/bas…
  // (+ ZQSD/WASD : on les bloque aussi pour éviter toute action du navigateur)
  const TOUCHES_BLOQUEES = new Set([
    "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " ", "Spacebar",
    "PageUp", "PageDown", "Home", "End",
    "z", "q", "s", "d", "w", "a", "Z", "Q", "S", "D", "W", "A",
  ]);
  let verrouActif = false;

  /** Bloque une touche de défilement (sauf si on tape dans un champ de texte). */
  function bloquerTouche(ev) {
    const cible = ev.target;
    if (cible && (cible.tagName === "INPUT" || cible.tagName === "TEXTAREA")) return;
    if (TOUCHES_BLOQUEES.has(ev.key)) ev.preventDefault();
  }
  /** Annule l'action par défaut (défilement à la molette ou au doigt). */
  function bloquer(ev) { ev.preventDefault(); }

  /**
   * Active le verrou : la page ne défile plus du tout.
   * passive:false est OBLIGATOIRE pour wheel/touchmove : sinon le navigateur
   * ignore preventDefault() (il défile sans attendre le script).
   */
  function verrouiller() {
    if (verrouActif) return;
    verrouActif = true;
    document.documentElement.classList.add("jeu-verrouille");
    window.addEventListener("keydown", bloquerTouche, { passive: false });
    window.addEventListener("wheel", bloquer, { passive: false });
    window.addEventListener("touchmove", bloquer, { passive: false });
  }

  /** Retire le verrou (écran de fin : on peut de nouveau défiler et cliquer). */
  function deverrouiller() {
    if (!verrouActif) return;
    verrouActif = false;
    document.documentElement.classList.remove("jeu-verrouille");
    window.removeEventListener("keydown", bloquerTouche);
    window.removeEventListener("wheel", bloquer);
    window.removeEventListener("touchmove", bloquer);
  }

  return { brancher: brancher, verrouiller: verrouiller, deverrouiller: deverrouiller };
})();
