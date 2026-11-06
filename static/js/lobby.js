/**
 * lobby.js — Créer / rejoindre une salle (code partageable)
 */
(function () {
  const btnCreer = document.getElementById("btn-creer");
  const msg = document.getElementById("creer-msg");
  const zone = document.getElementById("creer-zone");
  const codeEl = document.getElementById("creer-code");
  const lien = document.getElementById("lien-partie");
  const btnCopier = document.getElementById("btn-copier");
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
        // Affiche le code pour le partager avant d'entrer
        if (zone && codeEl && lien) {
          codeEl.textContent = data.code;
          lien.href = "/partie/" + data.code;
          zone.hidden = false;
          msg.textContent = "Envoie ce code à ton adversaire, puis entre dans la salle.";
          btnCreer.style.display = "none";
        } else {
          window.location.href = "/partie/" + data.code;
        }
      } catch (e) {
        msg.textContent = "Erreur réseau.";
        btnCreer.disabled = false;
      }
    });
  }

  if (btnCopier && codeEl) {
    btnCopier.addEventListener("click", async function () {
      const t = codeEl.textContent || "";
      try {
        await navigator.clipboard.writeText(t);
        btnCopier.textContent = "Copié !";
        setTimeout(function () { btnCopier.textContent = "Copier"; }, 1500);
      } catch (e) {
        btnCopier.textContent = t;
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
