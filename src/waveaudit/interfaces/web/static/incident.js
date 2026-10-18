// Suivi et résultat d'un incident (contrats §26, §28). Interroge /incidents/<id>/etat toutes
// les secondes, puis /incidents/<id>/resultat une fois terminé ; le filtre par sévérité est un
// groupe de boutons bascule (role="group", aria-pressed), EXPERIENCE « Page incident ».
(function () {
  "use strict";
  var script = document.currentScript;
  var idLot = script.getAttribute("data-id-lot");
  var texte = document.getElementById("etat-texte");
  var liste = document.getElementById("evenements");
  var resultatSection = document.getElementById("resultat");
  var resume = document.getElementById("resume");
  var corps = document.getElementById("detections-corps");
  var aucune = document.getElementById("aucune-detection");
  var telechargement = document.getElementById("telechargement");
  var recus = 0;
  var LIBELLES = { critique: "Critique", elevee: "Élevée", moyenne: "Moyenne", faible: "Faible" };
  var recits = [];
  var filtreActif = null;

  // Les 4 boutons de sévérité sont déjà dans le gabarit (DESIGN.md, rôles ARIA statiques) :
  // le JS ne fait que mettre à jour leur compte et gérer le filtre.
  Array.prototype.forEach.call(resume.querySelectorAll("button"), function (bouton) {
    bouton.addEventListener("click", function () {
      basculerFiltre(bouton.getAttribute("data-severite"));
    });
  });

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

  function rendreLigne(recit) {
    var tr = document.createElement("tr");
    [
      recit.detection.regle_id,
      LIBELLES[recit.severite] || recit.severite,
      recit.detection.debut,
      recit.detection.fin,
      (recit.detection.hotes || []).join(", "),
    ].forEach(function (valeur) {
      var td = document.createElement("td");
      td.textContent = valeur;
      tr.appendChild(td);
    });
    return tr;
  }

  function rendreDetections() {
    corps.innerHTML = "";
    var filtrees = filtreActif
      ? recits.filter(function (r) {
          return r.severite === filtreActif;
        })
      : recits;
    filtrees.forEach(function (recit) {
      corps.appendChild(rendreLigne(recit));
    });
  }

  function basculerFiltre(severite) {
    filtreActif = filtreActif === severite ? null : severite;
    Array.prototype.forEach.call(resume.querySelectorAll("button"), function (bouton) {
      var actif = bouton.getAttribute("data-severite") === filtreActif;
      bouton.setAttribute("aria-pressed", actif ? "true" : "false");
    });
    rendreDetections();
  }

  function rendreResume(parSeverite) {
    Array.prototype.forEach.call(resume.querySelectorAll("button"), function (bouton) {
      var severite = bouton.getAttribute("data-severite");
      bouton.textContent = (LIBELLES[severite] || severite) + " (" + (parSeverite[severite] || 0) + ")";
    });
  }

  function afficherResultat() {
    fetch("/incidents/" + encodeURIComponent(idLot) + "/resultat")
      .then(function (reponse) {
        return reponse.json();
      })
      .then(function (donnees) {
        recits = (donnees.rapport && donnees.rapport.recits) || [];
        rendreResume(donnees.par_severite || {});
        rendreDetections();
        resultatSection.hidden = false;
        aucune.hidden = donnees.total !== 0;
        var lien = document.createElement("a");
        lien.href = "/incidents/" + idLot + "/rapport-incident.docx";
        lien.textContent = "Télécharger le rapport (.docx)";
        telechargement.innerHTML = "";
        telechargement.appendChild(lien);
      });
  }

  function interroger() {
    fetch("/incidents/" + encodeURIComponent(idLot) + "/etat?depuis=" + recus)
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
          texte.textContent = "Analyse terminée.";
          afficherResultat();
          return;
        }
        if (donnees.etat === "echoue") {
          texte.textContent = "Analyse échouée : " + (donnees.erreur || "erreur inconnue");
          return;
        }
        if (donnees.etat === "interrompu") {
          // EXPERIENCE (State Patterns) : un incident interrompu est traité comme échoué.
          texte.textContent = "Analyse interrompue (processus arrêté).";
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
