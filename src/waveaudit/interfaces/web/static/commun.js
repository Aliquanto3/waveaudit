// Outils communs de l'interface (contrats §26, AD-22). Aucun script en ligne : la CSP les bloque.
// WaveAudit.envoyer(url, options) envoie une écriture (POST, PUT) avec l'en-tête X-CSRF-Token
// lu dans <meta name="csrf">. Sur un 403 csrf_invalide (serveur redémarré), le jeton est relu
// une fois par GET /api/jeton et la requête rejouée ; un second refus renvoie la réponse avec
// le message de redémarrage (WaveAudit.MESSAGE_REDEMARRAGE).
(function () {
  "use strict";

  var MESSAGE_REDEMARRAGE =
    "Le serveur a redémarré. Rechargez la page ; vos corrections enregistrées sont conservées.";

  function lireJeton() {
    var meta = document.querySelector('meta[name="csrf"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function ecrireJeton(jeton) {
    var meta = document.querySelector('meta[name="csrf"]');
    if (meta) {
      meta.setAttribute("content", jeton);
    }
  }

  function avecJeton(options) {
    var copie = Object.assign({}, options || {});
    var entetes = new Headers(copie.headers || {});
    entetes.set("X-CSRF-Token", lireJeton());
    copie.headers = entetes;
    copie.credentials = "same-origin";
    return copie;
  }

  function estRefusCsrf(reponse) {
    if (reponse.status !== 403) {
      return Promise.resolve(false);
    }
    return reponse
      .clone()
      .json()
      .then(function (corps) {
        return corps && corps.code === "csrf_invalide";
      })
      .catch(function () {
        return false;
      });
  }

  function envoyer(url, options) {
    return fetch(url, avecJeton(options)).then(function (reponse) {
      return estRefusCsrf(reponse).then(function (refus) {
        if (!refus) {
          return reponse;
        }
        return fetch("/api/jeton", { credentials: "same-origin" })
          .then(function (r) {
            return r.json();
          })
          .then(function (corps) {
            ecrireJeton(corps.jeton);
            return fetch(url, avecJeton(options));
          })
          .then(function (rejouee) {
            return estRefusCsrf(rejouee).then(function (encore) {
              rejouee.redemarrage = encore;
              return rejouee;
            });
          });
      });
    });
  }

  // Message d'une réponse d'erreur {detail, code} (§26), sinon un message générique.
  function messageErreur(reponse) {
    if (reponse.redemarrage) {
      return Promise.resolve(MESSAGE_REDEMARRAGE);
    }
    return reponse
      .json()
      .then(function (corps) {
        return (corps && corps.detail) || "Erreur inattendue (" + reponse.status + ").";
      })
      .catch(function () {
        return "Erreur inattendue (" + reponse.status + ").";
      });
  }

  window.WaveAudit = {
    envoyer: envoyer,
    messageErreur: messageErreur,
    MESSAGE_REDEMARRAGE: MESSAGE_REDEMARRAGE,
  };
})();
