/**
 * validation.js — Validation des formulaires CÔTÉ CLIENT (exigence NSI)
 * Les mêmes règles sont aussi appliquées côté serveur (Python).
 */

function setErr(name, msg) {
  const el = document.querySelector('.err[data-for="' + name + '"]');
  if (el) el.textContent = msg || "";
}

function clearErrs(form) {
  form.querySelectorAll(".err").forEach(function (e) { e.textContent = ""; });
}

function checkPseudo(value) {
  if (!value || value.trim().length < 3) return "Le pseudo doit faire au moins 3 caractères.";
  if (value.trim().length > 20) return "Le pseudo est trop long (max 20).";
  if (!/^[A-Za-z0-9_\-]+$/.test(value.trim())) {
    return "Lettres, chiffres, _ et - uniquement.";
  }
  return null;
}

function checkEmail(value) {
  if (!value || !value.trim()) return "L'e-mail est obligatoire.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())) return "Format d'e-mail invalide.";
  return null;
}

function checkMdp(value, obligatoire) {
  if (!value) return obligatoire ? "Le mot de passe est obligatoire." : null;
  if (value.length < 6) return "Au moins 6 caractères.";
  return null;
}

function initValidationInscription() {
  const form = document.getElementById("form-inscription");
  if (!form) return;
  form.addEventListener("submit", function (ev) {
    clearErrs(form);
    let ok = true;
    let e;
    e = checkPseudo(form.pseudo.value);
    if (e) { setErr("pseudo", e); ok = false; }
    e = checkEmail(form.email.value);
    if (e) { setErr("email", e); ok = false; }
    e = checkMdp(form.mot_de_passe.value, true);
    if (e) { setErr("mot_de_passe", e); ok = false; }
    if (form.mot_de_passe.value !== form.mot_de_passe2.value) {
      setErr("mot_de_passe2", "Les mots de passe ne correspondent pas.");
      ok = false;
    }
    if (!ok) ev.preventDefault();
  });
}

function initValidationConnexion() {
  const form = document.getElementById("form-connexion");
  if (!form) return;
  form.addEventListener("submit", function (ev) {
    if (!form.pseudo.value.trim() || !form.mot_de_passe.value) {
      ev.preventDefault();
    }
  });
}

function initValidationProfil() {
  const form = document.getElementById("form-profil");
  if (!form) return;
  form.addEventListener("submit", function (ev) {
    clearErrs(form);
    let ok = true;
    let e = checkEmail(form.email.value);
    if (e) { setErr("email", e); ok = false; }
    if (form.mot_de_passe.value || form.mot_de_passe2.value) {
      e = checkMdp(form.mot_de_passe.value, true);
      if (e) { setErr("mot_de_passe", e); ok = false; }
      if (form.mot_de_passe.value !== form.mot_de_passe2.value) {
        setErr("mot_de_passe2", "Les mots de passe ne correspondent pas.");
        ok = false;
      }
    }
    if (!ok) ev.preventDefault();
  });
}

function initValidationModifier() {
  const form = document.getElementById("form-modifier") || document.getElementById("form-nouveau");
  if (!form) return;
  form.addEventListener("submit", function (ev) {
    clearErrs(form);
    let ok = true;
    let e = checkPseudo(form.pseudo.value);
    if (e) { setErr("pseudo", e); ok = false; }
    e = checkEmail(form.email.value);
    if (e) { setErr("email", e); ok = false; }
    if (form.mot_de_passe && form.mot_de_passe.value) {
      e = checkMdp(form.mot_de_passe.value, true);
      if (e) { setErr("mot_de_passe", e); ok = false; }
    } else if (form.id === "form-nouveau") {
      e = checkMdp(form.mot_de_passe.value, true);
      if (e) { setErr("mot_de_passe", e); ok = false; }
    }
    if (!ok) ev.preventDefault();
  });
}

function initValidationNouveau() {
  initValidationModifier();
}

document.addEventListener("DOMContentLoaded", function () {
  initValidationInscription();
  initValidationConnexion();
  initValidationProfil();
});
