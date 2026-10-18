// Accueil (contrats §26) : le formulaire de dépôt part par fetch avec le jeton CSRF.
// Succès : le 303 vers /lots/<id> est suivi par fetch, la page navigue vers l'URL finale.
(function () {
  "use strict";
  var formulaire = document.getElementById("depot");
  var message = document.getElementById("depot-message");
  if (!formulaire) {
    return;
  }
  var bouton = formulaire.querySelector('button[type="submit"]');

  formulaire.addEventListener("submit", function (evenement) {
    evenement.preventDefault();
    message.textContent = "";
    bouton.disabled = true;
    window.WaveAudit.envoyer(formulaire.action, {
      method: "POST",
      body: new FormData(formulaire),
    })
      .then(function (reponse) {
        if (reponse.ok && reponse.redirected) {
          window.location.assign(reponse.url);
          return;
        }
        return window.WaveAudit.messageErreur(reponse).then(function (texte) {
          message.textContent = texte;
          bouton.disabled = false;
        });
      })
      .catch(function () {
        message.textContent = "Le serveur ne répond pas. Réessayez dans un instant.";
        bouton.disabled = false;
      });
  });
})();
