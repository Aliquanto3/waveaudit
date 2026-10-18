// Accueil (contrats §26) : choix du workflow (fiches / incident, EXPERIENCE « Accueil ») et
// envoi des formulaires de dépôt par fetch avec le jeton CSRF (POST /lots ou /incidents).
// Succès : le 303 vers /lots/<id> ou /incidents/<id> est suivi par fetch, la page navigue vers
// l'URL finale ; refus : le message d'erreur codé s'affiche et aucun lot n'est créé.
(function () {
  "use strict";
  var message = document.getElementById("depot-message");
  var formulaires = document.querySelectorAll("form.depot");
  var cartes = document.querySelectorAll(".carte-workflow");

  function choisirWorkflow(workflow) {
    Array.prototype.forEach.call(cartes, function (carte) {
      var actif = carte.getAttribute("data-workflow") === workflow;
      carte.setAttribute("aria-pressed", actif ? "true" : "false");
    });
    Array.prototype.forEach.call(formulaires, function (formulaire) {
      formulaire.hidden = formulaire.getAttribute("data-workflow") !== workflow;
    });
    if (message) {
      message.textContent = "";
    }
  }

  Array.prototype.forEach.call(cartes, function (carte) {
    carte.addEventListener("click", function () {
      choisirWorkflow(carte.getAttribute("data-workflow"));
    });
  });

  Array.prototype.forEach.call(formulaires, function (formulaire) {
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
  });
})();
