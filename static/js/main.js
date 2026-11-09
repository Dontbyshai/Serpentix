/**
 * main.js — Script commun à toutes les pages.
 * Gère le bouton ☰ qui ouvre / ferme le menu de navigation sur mobile.
 */
(function () {
  const toggle = document.getElementById("nav-toggle");
  const nav = document.getElementById("main-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      const ouvert = nav.classList.toggle("open");   // ajoute ou retire la classe
      toggle.setAttribute("aria-expanded", ouvert ? "true" : "false"); // accessibilité
    });
  }
})();
