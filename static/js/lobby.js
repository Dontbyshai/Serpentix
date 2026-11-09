/**
 * lobby.js — Créer / rejoindre une salle de jeu
 */
(function () {
  const btnCreer = document.getElementById("btn-creer");
  const msg = document.getElementById("creer-msg");
  const form = document.getElementById("form-rejoindre");
  const err = document.getElementById("rejoindre-err");

  if (btnCreer) {
    btnCreer.addEventListener("click", async function () {
      btnCreer.disabled = true;
      msg.textContent = "Création…";
      try {
        const res = await fetch("/api/partie/creer", { method: "POST" });
        const data = await res.json();
        if (!data.ok) {
          msg.textContent = data.erreur || "Erreur";
          btnCreer.disabled = false;
          return;
        }
        msg.textContent = "Code : " + data.code + " — redirection…";
        window.location.href = "/partie/" + data.code;
      } catch (e) {
        msg.textContent = "Erreur réseau.";
        btnCreer.disabled = false;
      }
    });
  }

  if (form) {
    form.addEventListener("submit", async function (ev) {
      ev.preventDefault();
      err.textContent = "";
      const code = (form.code.value || "").trim().toUpperCase();
      if (!code || code.length < 4) {
        err.textContent = "Code invalide.";
        return;
      }
      try {
        const res = await fetch("/api/partie/rejoindre", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code: code }),
        });
        const data = await res.json();
        if (!data.ok) {
          err.textContent = data.erreur || "Impossible de rejoindre.";
          return;
        }
        window.location.href = "/partie/" + data.code;
      } catch (e) {
        err.textContent = "Erreur réseau.";
      }
    });
  }
})();
