// Suivi de l'état d'un lot (contrats §18). Interroge /lots/<id>/etat toutes les secondes.
(function () {
  "use strict";
  var script = document.currentScript;
  var idLot = script.getAttribute("data-id-lot");
  var texte = document.getElementById("etat-texte");
  var liste = document.getElementById("evenements");
  var telechargement = document.getElementById("telechargement");
  var recus = 0; // événements déjà affichés : seuls les suivants sont redemandés et ajoutés

  function ajouterEvenements(evenements) {
    recus += evenements.length;
    evenements.forEach(function (evenement) {
      var ligne = document.createElement("li");
      var morceaux = [evenement.type];
      if (evenement.note) {
        morceaux.push(evenement.note);
      }
      if (evenement.statut) {
        morceaux.push(evenement.statut);
      }
      ligne.textContent = morceaux.join(" — ");
      liste.appendChild(ligne);
    });
  }

  function interroger() {
    fetch("/lots/" + encodeURIComponent(idLot) + "/etat?depuis=" + recus)
      .then(function (reponse) {
        if (reponse.status === 404) {
          texte.textContent = "Lot inconnu.";
          return null;
        }
        return reponse.json();
      })
      .then(function (donnees) {
        if (donnees === null) {
          return;
        }
        ajouterEvenements(donnees.evenements || []);
        if (donnees.etat === "termine") {
          texte.textContent = "Lot terminé.";
          var lien = document.createElement("a");
          lien.href = "/lots/" + idLot + "/rapport.docx";
          lien.textContent = "Télécharger le rapport (.docx)";
          telechargement.innerHTML = "";
          telechargement.appendChild(lien);
          return;
        }
        if (donnees.etat === "echoue") {
          texte.textContent = "Lot échoué : " + (donnees.erreur || "erreur inconnue");
          return;
        }
        setTimeout(interroger, 1000);
      })
      .catch(function () {
        setTimeout(interroger, 1000);
      });
  }

  interroger();
})();
