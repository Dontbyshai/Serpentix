/**
 * validation.js — Validation des formulaires CÔTÉ CLIENT (exigence NSI).
 *
 * But : prévenir l'utilisateur TOUT DE SUITE, sans attendre le serveur.
 * Ce n'est PAS une sécurité : n'importe qui peut désactiver JavaScript ou
 * envoyer une requête à la main. C'est pourquoi les MÊMES règles sont
 * vérifiées à nouveau en Python (fonctions valider_* dans app.py).
 *
 * Chaque fonction check… renvoie null si la valeur est correcte, sinon le
 * message d'erreur à afficher.
 */

/**
 * Écrit un message dans le <span class="err" data-for="nom"> du champ.
 * @param {HTMLFormElement} form
 * @param {string} name - nom du champ
 * @param {string} msg - message ("" pour effacer)
 */
function setErr(form, name, msg) {
  const el = form.querySelector('.err[data-for="' + name + '"]');
  if (el) el.textContent = msg || "";
}

/** Efface toutes les erreurs du formulaire. @param {HTMLFormElement} form */
function clearErrs(form) {
  form.querySelectorAll(".err").forEach(function (e) { e.textContent = ""; });
}

/** @param {string} value @returns {string|null} */
function checkPseudo(value) {
  const v = (value || "").trim();
  if (v.length < 3) return "Le pseudo doit faire au moins 3 caractères.";
  if (v.length > 20) return "Le pseudo est trop long (max 20).";
  // Expression régulière : uniquement lettres, chiffres, _ et -
  if (!/^[A-Za-z0-9_\-]+$/.test(v)) return "Lettres, chiffres, _ et - uniquement.";
  return null;
}

/** @param {string} value @returns {string|null} */
function checkEmail(value) {
  const v = (value || "").trim();
  if (!v) return "L'e-mail est obligatoire.";
  if (v.length > 100) return "E-mail trop long.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return "Format d'e-mail invalide.";
  return null;
}

/**
 * @param {string} value
 * @param {boolean} obligatoire - faux = champ vide accepté (« inchangé »)
 * @returns {string|null}
 */
function checkMdp(value, obligatoire) {
  if (!value) return obligatoire ? "Le mot de passe est obligatoire." : null;
  if (value.length < 6) return "Au moins 6 caractères.";
  if (value.length > 100) return "Mot de passe trop long.";
  return null;
}

/**
 * Branche un validateur sur l'événement « submit » d'un formulaire.
 * Si la fonction regles() trouve une erreur, on bloque l'envoi
 * (ev.preventDefault) et les messages restent affichés.
 * @param {string} id - id HTML du formulaire
 * @param {function(HTMLFormElement): boolean} regles - renvoie true si tout est valide
 */
function brancherValidation(id, regles) {
  const form = document.getElementById(id);
  if (!form) return;
  form.addEventListener("submit", function (ev) {
    clearErrs(form);
    if (!regles(form)) ev.preventDefault();
  });
}

/**
 * Vérifie un champ et affiche son erreur.
 * @returns {boolean} true si le champ est valide
 */
function verifier(form, name, erreur) {
  if (erreur) { setErr(form, name, erreur); return false; }
  return true;
}

document.addEventListener("DOMContentLoaded", function () {
  // Inscription : tous les champs + confirmation identique
  brancherValidation("form-inscription", function (f) {
    let ok = verifier(f, "pseudo", checkPseudo(f.pseudo.value));
    ok = verifier(f, "email", checkEmail(f.email.value)) && ok;
    ok = verifier(f, "mot_de_passe", checkMdp(f.mot_de_passe.value, true)) && ok;
    if (f.mot_de_passe.value !== f.mot_de_passe2.value) {
      ok = verifier(f, "mot_de_passe2", "Les mots de passe ne correspondent pas.") && ok;
    }
    return ok;
  });

  // Connexion : les deux champs doivent être remplis
  brancherValidation("form-connexion", function (f) {
    let ok = verifier(f, "pseudo", f.pseudo.value.trim() ? null : "Entre ton pseudo.");
    ok = verifier(f, "mot_de_passe", f.mot_de_passe.value ? null : "Entre ton mot de passe.") && ok;
    return ok;
  });

  // Profil : e-mail + nouveau mot de passe optionnel (mais confirmé)
  brancherValidation("form-profil", function (f) {
    let ok = verifier(f, "email", checkEmail(f.email.value));
    if (f.mot_de_passe.value || f.mot_de_passe2.value) {
      ok = verifier(f, "mot_de_passe", checkMdp(f.mot_de_passe.value, true)) && ok;
      if (f.mot_de_passe.value !== f.mot_de_passe2.value) {
        ok = verifier(f, "mot_de_passe2", "Les mots de passe ne correspondent pas.") && ok;
      }
    }
    return ok;
  });

  // Gestion joueurs : modifier (mot de passe facultatif) et créer (obligatoire)
  ["form-modifier", "form-nouveau"].forEach(function (id) {
    brancherValidation(id, function (f) {
      let ok = verifier(f, "pseudo", checkPseudo(f.pseudo.value));
      ok = verifier(f, "email", checkEmail(f.email.value)) && ok;
      ok = verifier(f, "mot_de_passe", checkMdp(f.mot_de_passe.value, id === "form-nouveau")) && ok;
      return ok;
    });
  });
});
