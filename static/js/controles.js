/**
 * controles.js — Contrôles du serpent, PARTAGÉS par le solo et le 1v1.
 *
 * Trois façons de diriger le serpent :
 *   1) clavier : flèches ou ZQSD / WASD ;
 *   2) glisser le doigt sur le plateau (téléphone, tablette) ;
 *   3) boutons fléchés à l'écran (élément .dpad, visible sur mobile).
 * Chaque action appelle la même fonction rappel(dx, dy).
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

  return { brancher: brancher };
})();
