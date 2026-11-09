/**
 * lobby.js — Page « Jouer » : créer une salle (2 ou 3 joueurs) ou rejoindre avec un code.
 * Communique avec Flask par fetch() (requêtes HTTP en arrière-plan, sans
 * recharger la page) vers /api/partie/creer et /api/partie/rejoindre.
 */
(function () {
  const formCreer = document.getElementById("form-creer");
  const btnCreer = document.getElementById("btn-creer");
  const msg = document.getElementById("creer-msg");
  const zone = document.getElementById("creer-zone");
  const codeEl = document.getElementById("creer-code");
  const lien = document.getElementById("lien-partie");
  const btnCopier = document.getElementById("btn-copier");
  const form = document.getElementById("form-rejoindre");
  const err = document.getElementById("rejoindre-err");
  // Jeton anti-CSRF à joindre à chaque POST (vérifié par app.py)
  const CSRF = document.querySelector('meta[name="csrf-token"]').content;
  const FORMAT_CODE = /^[A-Z0-9]{6}$/;      // même règle que code_valide() en Python

  // --- Créer une salle -----------------------------------------------------
  if (formCreer) {
    formCreer.addEventListener("submit", async function (ev) {
      ev.preventDefault();                   // on envoie nous-mêmes avec fetch()
      // Validation CLIENT : on lit le bouton radio coché, seules 2 et 3 sont acceptées
      const choix = formCreer.querySelector('input[name="nb_joueurs"]:checked');
      const nb = choix ? parseInt(choix.value, 10) : 0;
      if (nb !== 2 && nb !== 3) {
        msg.textContent = "Choisis 2 ou 3 joueurs.";
        return;
      }
      btnCreer.disabled = true;              // évite de créer 2 salles en double-cliquant
      msg.textContent = "Création…";
      try {
        const res = await fetch("/api/partie/creer", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF },
          body: JSON.stringify({ nb_joueurs: nb }),
        });
        const data = await res.json();
        if (!data.ok) {
          msg.textContent = data.erreur || "Erreur";
          btnCreer.disabled = false;
          return;
        }
        // On montre le code à partager avant d'entrer dans la salle
        codeEl.textContent = data.code;
        lien.href = "/partie/" + data.code;
        zone.hidden = false;
        msg.textContent = data.nb_joueurs === 3
          ? "Salle de 3 : envoie ce code à tes DEUX adversaires, puis entre dans la salle."
          : "Duel : envoie ce code à ton adversaire, puis entre dans la salle.";
        formCreer.hidden = true;
      } catch (e) {
        msg.textContent = "Erreur réseau.";
        btnCreer.disabled = false;
      }
    });
  }

  // --- Copier le code dans le presse-papiers --------------------------------
  if (btnCopier) {
    btnCopier.addEventListener("click", async function () {
      try {
        await navigator.clipboard.writeText(codeEl.textContent || "");
        btnCopier.textContent = "Copié !";
        setTimeout(function () { btnCopier.textContent = "Copier"; }, 1500);
      } catch (e) {
        btnCopier.textContent = "Copie impossible";   // ex. site en http sur mobile
      }
    });
  }

  // --- Rejoindre avec un code (validation client puis serveur) ------------
  if (form) {
    form.code.addEventListener("input", function () {
      // Saisie confortable : majuscules automatiques, caractères interdits retirés
      form.code.value = form.code.value.toUpperCase().replace(/[^A-Z0-9]/g, "");
    });
    form.addEventListener("submit", async function (ev) {
      ev.preventDefault();                   // on gère l'envoi nous-mêmes
      err.textContent = "";
      const code = (form.code.value || "").trim().toUpperCase();
      if (!FORMAT_CODE.test(code)) {
        err.textContent = "Le code fait 6 lettres ou chiffres.";
        return;
      }
      try {
        const res = await fetch("/api/partie/rejoindre", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF },
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
