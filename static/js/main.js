/**
 * main.js — Scripts communs Serpentix
 * Menu mobile + petites utilitaires
 */
(function () {
  const toggle = document.getElementById("nav-toggle");
  const nav = document.getElementById("main-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      nav.classList.toggle("open");
    });
  }
})();
