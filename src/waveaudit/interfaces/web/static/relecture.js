// Écran de relecture d'un lot (contrats §25, §26 ; EXPERIENCE.md « Relecture »). Reprend le
// suivi (barre/journal, comme etat.js) puis bascule sur la relecture (tiroir, candidats ou
// catalogue, fiche, export) dès que le lot n'est plus en_cours. Un seul PUT de correction en
// vol par entrée (le dernier corps en file), confirmation avant un changement de candidat sur
// une fiche corrigée ou validée, réessai après 3 s sur 503/erreur réseau, dialogues fermables
// par Échap avec retour du focus.
(function () {
  "use strict";

  var script = document.currentScript;
  var idLot = script.getAttribute("data-id-lot");

  var elSuivi = document.getElementById("suivi");
  var elEtatTexte = document.getElementById("etat-texte");
  var elEvenements = document.getElementById("evenements");
  var elTelechargement = document.getElementById("telechargement");

  var elRelecture = document.getElementById("relecture");
  var elErreur = document.getElementById("relecture-erreur");
  var elTiroirConteneur = document.getElementById("tiroir-conteneur");
  var elTiroirBascule = document.getElementById("tiroir-bascule");
  var elTiroirListe = document.getElementById("tiroir-liste");
  var elPanneauNote = document.getElementById("panneau-note");
  var elNoteCorps = document.getElementById("note-corps");
  var elCandidatsBarre = document.getElementById("candidats-barre");
  var elCatalogueZone = document.getElementById("catalogue-zone");
  var elCatalogueFiltre = document.getElementById("catalogue-filtre");
  var elCatalogueListe = document.getElementById("catalogue-liste");
  var elPanneauFiche = document.getElementById("panneau-fiche");
  var elGenerationEnCours = document.getElementById("generation-en-cours");
  var elMotifs = document.getElementById("motifs");
  var elMotifsListe = document.getElementById("motifs-liste");
  var elFormulaire = document.getElementById("formulaire-fiche");
  var elTitre = document.getElementById("champ-titre");
  var elDescription = document.getElementById("champ-description");
  var elImpact = document.getElementById("champ-impact");
  var elRecommandation = document.getElementById("champ-recommandation");
  var elCvss = document.getElementById("champ-cvss");
  var elCvssPastille = document.getElementById("cvss-pastille");
  var elCvssErreur = document.getElementById("cvss-erreur");
  var elReferencesListe = document.getElementById("references-liste");
  var elIndicateur = document.getElementById("indicateur-enregistrement");
  var elBoutonPrecedente = document.getElementById("bouton-precedente");
  var elBoutonSuivante = document.getElementById("bouton-suivante");
  var elBoutonValider = document.getElementById("bouton-valider");
  var elRaisonValidation = document.getElementById("raison-validation");
  var elBoutonExportFinal = document.getElementById("bouton-exporter-final");
  var elBoutonExportBrouillon = document.getElementById("bouton-exporter-brouillon");

  var elDialogCandidat = document.getElementById("dialog-candidat");
  var elDialogCandidatTexte = document.getElementById("dialog-candidat-texte");
  var elDialogCandidatAnnuler = document.getElementById("dialog-candidat-annuler");
  var elDialogCandidatConfirmer = document.getElementById("dialog-candidat-confirmer");

  var elDialogConflit = document.getElementById("dialog-conflit");
  var elDialogConflitGarder = document.getElementById("dialog-conflit-garder");
  var elDialogConflitRecharger = document.getElementById("dialog-conflit-recharger");

  var elDialogExport = document.getElementById("dialog-export");
  var elDialogExportTexte = document.getElementById("dialog-export-texte");
  var elDialogExportAnnuler = document.getElementById("dialog-export-annuler");
  var elDialogExportConfirmer = document.getElementById("dialog-export-confirmer");

  var recus = 0;
  var entrees = [];
  var langue = "fr";
  var nonValidees = 0;
  var focalIndex = -1; // ligne en surbrillance dans le tiroir (navigation clavier)
  var courante = null; // dernière entrée chargée (forme EntreeRelecture)
  var ficheCourante = null;
  var candidatsDetail = [];
  var generable = false;
  var modifiable = false;
  var catalogue = null; // chargé une fois, à la demande
  var pendingBody = null; // dernier corps de correction en file
  var enVol = false;
  var minuteurAntiRebond = null;
  var corpsEnPreparation = false; // un changement vient d'être chargé : ignorer le premier input
  var dialogueOuvert = null;
  var elementAvantDialogue = null;

  // --- Suivi (reprend etat.js) ---------------------------------------------------------------

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
      elEvenements.appendChild(ligne);
    });
  }

  function interrogerSuivi() {
    fetch("/lots/" + encodeURIComponent(idLot) + "/etat?depuis=" + recus)
      .then(function (reponse) {
        if (reponse.status === 404) {
          elEtatTexte.textContent = "Lot inconnu.";
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
          elEtatTexte.textContent = "Lot terminé.";
          afficherRelecture();
          return;
        }
        if (donnees.etat === "echoue") {
          elEtatTexte.textContent = "Lot échoué : " + (donnees.erreur || "erreur inconnue");
          afficherRelecture();
          return;
        }
        if (donnees.etat === "interrompu") {
          elEtatTexte.textContent = "Lot interrompu (processus arrêté).";
          afficherRelecture();
          return;
        }
        setTimeout(interrogerSuivi, 1000);
      })
      .catch(function () {
        setTimeout(interrogerSuivi, 1000);
      });
  }

  // --- Relecture : chargement de la liste --------------------------------------------------

  function afficherRelecture() {
    elRelecture.hidden = false;
    chargerListe();
  }

  var LIBELLES_STATUT = {
    attente: "en attente",
    ecartee: "écartée",
    fiche_a_valider: "à valider",
    fiche_validee: "validée",
  };

  function libelleStatut(entree) {
    if (entree.etat === "fiche") {
      return LIBELLES_STATUT["fiche_" + entree.statut_relecture] || entree.statut_relecture;
    }
    return LIBELLES_STATUT[entree.etat] || entree.etat;
  }

  function chargerListe() {
    fetch("/lots/" + encodeURIComponent(idLot) + "/relecture")
      .then(function (reponse) {
        return reponse.json();
      })
      .then(function (donnees) {
        entrees = donnees.entrees || [];
        langue = donnees.langue || "fr";
        nonValidees = donnees.non_validees || 0;
        elPanneauNote.setAttribute("lang", langue);
        elPanneauFiche.setAttribute("lang", langue);
        rendreTiroir();
        if (entrees.length && focalIndex === -1) {
          var premiere = entrees[0].index;
          selectionner(premiere);
          ouvrirEntree(premiere);
        }
      })
      .catch(function () {
        afficherErreur("Le serveur ne répond pas. Rechargez la page dans un instant.");
      });
  }

  function rendreTiroir() {
    Array.prototype.forEach.call(
      elTiroirListe.querySelectorAll('li[role="option"]:not(#tiroir-exemple)'),
      function (li) {
        li.remove();
      }
    );
    entrees.forEach(function (entree) {
      var li = document.createElement("li");
      li.setAttribute("role", "option");
      li.setAttribute("data-index", String(entree.index));
      li.setAttribute("aria-selected", entree.index === focalIndex ? "true" : "false");
      li.textContent = (entree.titre || entree.note) + " — " + libelleStatut(entree);
      li.addEventListener("click", function () {
        selectionner(entree.index);
        ouvrirEntree(entree.index);
      });
      elTiroirListe.appendChild(li);
    });
    if (!elTiroirListe.hasAttribute("tabindex")) {
      elTiroirListe.setAttribute("tabindex", "0");
    }
  }

  function selectionner(index) {
    focalIndex = index;
    Array.prototype.forEach.call(elTiroirListe.querySelectorAll('li[role="option"]'), function (li) {
      li.setAttribute("aria-selected", li.getAttribute("data-index") === String(index) ? "true" : "false");
    });
  }

  elTiroirListe.addEventListener("keydown", function (evenement) {
    if (!entrees.length) {
      return;
    }
    var positions = entrees.map(function (e) {
      return e.index;
    });
    var rang = positions.indexOf(focalIndex);
    if (evenement.key === "ArrowDown") {
      evenement.preventDefault();
      selectionner(positions[Math.min(rang + 1, positions.length - 1)]);
    } else if (evenement.key === "ArrowUp") {
      evenement.preventDefault();
      selectionner(positions[Math.max(rang - 1, 0)]);
    } else if (evenement.key === "Enter" || evenement.key === " ") {
      evenement.preventDefault();
      ouvrirEntree(focalIndex);
    }
  });

  elTiroirBascule.addEventListener("click", function () {
    var repli = elTiroirConteneur.classList.toggle("tiroir-repli");
    elTiroirBascule.setAttribute("aria-expanded", repli ? "false" : "true");
  });

  // --- Relecture : une entrée ---------------------------------------------------------------

  var minuteurGeneration = null;

  function ouvrirEntree(index) {
    annulerAntiRebond();
    if (minuteurGeneration) {
      clearTimeout(minuteurGeneration);
      minuteurGeneration = null;
    }
    fetch("/lots/" + encodeURIComponent(idLot) + "/entrees/" + index)
      .then(function (reponse) {
        if (!reponse.ok) {
          return window.WaveAudit.messageErreur(reponse).then(function (message) {
            afficherErreur(message);
            return null;
          });
        }
        return reponse.json();
      })
      .then(function (donnees) {
        if (!donnees) {
          return;
        }
        rendreEntree(index, donnees);
      });
  }

  function rendreEntree(index, donnees) {
    courante = donnees.entree;
    ficheCourante = donnees.fiche_courante;
    candidatsDetail = donnees.candidats_detail || [];
    generable = donnees.generable;
    modifiable = donnees.modifiable;

    elNoteCorps.textContent = courante.source ? courante.source.corps : courante.note;

    var nonRattachee =
      courante.etat === "ecartee" && courante.ecartee && courante.ecartee.statut === "non_rattachee";
    elCandidatsBarre.hidden = nonRattachee;
    elCatalogueZone.hidden = !nonRattachee;
    if (nonRattachee) {
      chargerCatalogue();
    } else {
      rendreCandidats();
    }

    elGenerationEnCours.hidden = courante.generation !== "en_cours";
    elPanneauFiche.setAttribute("aria-busy", courante.generation === "en_cours" ? "true" : "false");

    corpsEnPreparation = true;
    if (ficheCourante) {
      elTitre.value = ficheCourante.titre;
      elDescription.value = ficheCourante.description;
      elImpact.value = ficheCourante.impact;
      elRecommandation.value = ficheCourante.recommandation;
      elCvss.value = ficheCourante.cvss.vecteur;
      rendreCvss(ficheCourante.cvss.vecteur);
      rendreReferences(ficheCourante.references);
    } else {
      elTitre.value = "";
      elDescription.value = "";
      elImpact.value = "";
      elRecommandation.value = "";
      elCvss.value = "";
      rendreCvss("");
      rendreReferences([]);
    }
    corpsEnPreparation = false;

    var motifs =
      donnees.entree.fiche_generee && donnees.entree.fiche_generee.motifs
        ? donnees.entree.fiche_generee.motifs
        : [];
    elMotifs.hidden = motifs.length === 0;
    elMotifsListe.innerHTML = "";
    motifs.forEach(function (motif) {
      var li = document.createElement("li");
      li.textContent = motif.detail + " (signalé à la génération)";
      elMotifsListe.appendChild(li);
    });

    var champMotifie = ficheCourante !== null && !modifiable;
    [elTitre, elDescription, elImpact, elRecommandation, elCvss].forEach(function (champ) {
      champ.disabled = champMotifie || ficheCourante === null;
    });
    elBoutonValider.disabled = !modifiable || ficheCourante === null || !cvssValide(elCvss.value);
    elRaisonValidation.hidden = elBoutonValider.disabled ? false : true;

    if (courante.generation === "en_cours") {
      minuteurGeneration = setTimeout(function () {
        ouvrirEntree(index);
      }, 1000);
    }
  }

  function rendreCandidats() {
    for (var rang = 1; rang <= 3; rang += 1) {
      var bouton = document.getElementById("onglet-candidat-" + rang);
      var detail = candidatsDetail[rang - 1];
      if (detail) {
        bouton.hidden = false;
        bouton.textContent = detail.titre + " (" + detail.score.toFixed(2) + ")";
        bouton.setAttribute("data-constat-id", detail.id);
        var choisi = courante.candidat_choisi === detail.id;
        bouton.setAttribute("aria-selected", choisi ? "true" : "false");
        bouton.disabled = !generable || choisi;
      } else {
        bouton.hidden = true;
        bouton.removeAttribute("data-constat-id");
      }
    }
  }

  document.querySelectorAll('#candidats-barre [role="tab"]').forEach(function (bouton) {
    bouton.addEventListener("click", function () {
      var constatId = bouton.getAttribute("data-constat-id");
      if (constatId) {
        demanderCandidat(constatId);
      }
    });
  });

  function chargerCatalogue() {
    if (catalogue !== null) {
      rendreCatalogue();
      return;
    }
    fetch("/lots/" + encodeURIComponent(idLot) + "/catalogue")
      .then(function (reponse) {
        return reponse.json();
      })
      .then(function (donnees) {
        catalogue = donnees.constats || [];
        rendreCatalogue();
      });
  }

  function rendreCatalogue() {
    Array.prototype.forEach.call(
      elCatalogueListe.querySelectorAll('li[role="option"]:not(#catalogue-exemple)'),
      function (li) {
        li.remove();
      }
    );
    (catalogue || []).forEach(function (constat) {
      var li = document.createElement("li");
      li.setAttribute("role", "option");
      li.setAttribute("aria-selected", "false");
      li.setAttribute("data-id", constat.id);
      li.textContent = constat.id + " — " + constat.titre;
      li.addEventListener("click", function () {
        if (generable) {
          demanderCandidat(constat.id);
        }
      });
      elCatalogueListe.appendChild(li);
    });
  }

  elCatalogueFiltre.addEventListener("input", function () {
    var filtre = elCatalogueFiltre.value.trim().toLowerCase();
    Array.prototype.forEach.call(
      elCatalogueListe.querySelectorAll('li[role="option"]:not(#catalogue-exemple)'),
      function (li) {
        li.hidden = filtre !== "" && li.textContent.toLowerCase().indexOf(filtre) === -1;
      }
    );
  });

  // --- CVSS (aperçu local, jamais envoyé) ----------------------------------------------------

  var POIDS_METRIQUES = { AV: 0.2, AC: 0.1, PR: 0.1, UI: 0.1, S: 0.1, C: 0.1, I: 0.1, A: 0.1 };

  function cvssValide(vecteur) {
    return /^CVSS:3\.1\/AV:[NALP]\/AC:[LH]\/PR:[NLH]\/UI:[NR]\/S:[UC]\/C:[NLH]\/I:[NLH]\/A:[NLH]$/.test(
      (vecteur || "").trim()
    );
  }

  function severiteApprochee(vecteur) {
    // Aperçu grossier (ordre de grandeur), jamais envoyé : le score qui fait foi vient du serveur.
    var valide = cvssValide(vecteur);
    if (!valide) {
      return null;
    }
    var haut = (vecteur.match(/:H\b/g) || []).length + (vecteur.match(/:C\b|:A\b/g) || []).length;
    if (haut >= 5) {
      return "critique";
    }
    if (haut >= 3) {
      return "elevee";
    }
    if (haut >= 1) {
      return "moyenne";
    }
    return "faible";
  }

  function rendreCvss(vecteur) {
    var severite = severiteApprochee(vecteur);
    elCvssPastille.className = severite ? "severite-" + severite : "";
    elCvssPastille.textContent = severite
      ? { faible: "Faible", moyenne: "Moyenne", elevee: "Élevée", critique: "Critique" }[severite]
      : "";
    var invalide = (vecteur || "").trim() !== "" && severite === null;
    elCvss.setAttribute("aria-invalid", invalide ? "true" : "false");
    elCvssErreur.hidden = !invalide;
  }

  elCvss.addEventListener("input", function () {
    rendreCvss(elCvss.value);
  });

  // --- Références (sous-ensemble ordonné, retrait seul) --------------------------------------

  var referencesCourantes = [];

  function rendreReferences(references) {
    referencesCourantes = references.slice();
    elReferencesListe.innerHTML = "";
    referencesCourantes.forEach(function (reference) {
      var li = document.createElement("li");
      var texte = document.createElement("span");
      texte.textContent = reference.titre;
      li.appendChild(texte);
      var bouton = document.createElement("button");
      bouton.type = "button";
      bouton.textContent = "Retirer";
      bouton.setAttribute("aria-label", "Retirer la référence " + reference.titre);
      bouton.addEventListener("click", function () {
        referencesCourantes = referencesCourantes.filter(function (r) {
          return r.id !== reference.id;
        });
        rendreReferences(referencesCourantes);
        declencherEnregistrement();
      });
      li.appendChild(bouton);
      elReferencesListe.appendChild(li);
    });
  }

  // --- Enregistrement automatique (anti-rebond ~800 ms, corps complet, un seul PUT en vol) ---

  function annulerAntiRebond() {
    if (minuteurAntiRebond) {
      clearTimeout(minuteurAntiRebond);
      minuteurAntiRebond = null;
    }
  }

  function declencherEnregistrement() {
    if (corpsEnPreparation || !modifiable || ficheCourante === null) {
      return;
    }
    annulerAntiRebond();
    minuteurAntiRebond = setTimeout(demarrerEnregistrement, 800);
  }

  [elTitre, elDescription, elImpact, elRecommandation, elCvss].forEach(function (champ) {
    champ.addEventListener("input", declencherEnregistrement);
  });

  function corpsCourant() {
    return {
      titre: elTitre.value,
      description: elDescription.value,
      impact: elImpact.value,
      recommandation: elRecommandation.value,
      cvss_vecteur: elCvss.value,
      references: referencesCourantes.map(function (r) {
        return r.id;
      }),
    };
  }

  function demarrerEnregistrement() {
    var corps = corpsCourant();
    if (enVol) {
      pendingBody = corps;
      return;
    }
    envoyerCorrection(corps);
  }

  function envoyerCorrection(corps) {
    enVol = true;
    elIndicateur.textContent = "Enregistrement…";
    var requete = Object.assign({ version: courante.version }, corps);
    window.WaveAudit.envoyer("/lots/" + encodeURIComponent(idLot) + "/entrees/" + courante.index + "/correction", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requete),
    })
      .then(function (reponse) {
        return reponse.json().then(function (corps_reponse) {
          return { reponse: reponse, corps: corps_reponse };
        });
      })
      .then(function (resultat) {
        enVol = false;
        if (resultat.reponse.status === 409 && resultat.corps.code === "conflit_version") {
          ouvrirDialogueConflit(resultat.corps.entree, corps);
          return;
        }
        if (!resultat.reponse.ok) {
          elIndicateur.textContent =
            "La correction n'a pas pu être enregistrée. Nouvelle tentative dans quelques secondes.";
          setTimeout(function () {
            envoyerCorrection(corps);
          }, 3000);
          return;
        }
        courante = resultat.corps.entree;
        elBoutonValider.disabled = !modifiable || !cvssValide(elCvss.value);
        elRaisonValidation.hidden = elBoutonValider.disabled ? false : true;
        majLigneTiroir(courante);
        elIndicateur.textContent = "Enregistré";
        if (pendingBody) {
          var suivant = pendingBody;
          pendingBody = null;
          envoyerCorrection(suivant);
        }
      })
      .catch(function () {
        enVol = false;
        elIndicateur.textContent =
          "La correction n'a pas pu être enregistrée. Nouvelle tentative dans quelques secondes.";
        setTimeout(function () {
          envoyerCorrection(corps);
        }, 3000);
      });
  }

  function majLigneTiroir(entree) {
    entrees = entrees.map(function (e) {
      return e.index === entree.index
        ? Object.assign({}, e, {
            statut_relecture: entree.statut_relecture,
            version: entree.version,
            titre: e.titre,
          })
        : e;
    });
    rendreTiroir();
    selectionner(focalIndex);
  }

  function ouvrirDialogueConflit(entreeServeur, corpsConserve) {
    courante = entreeServeur;
    ouvrirDialogue(elDialogConflit, elDialogConflitGarder);
    elDialogConflitGarder.onclick = function () {
      fermerDialogue();
      envoyerCorrection(corpsConserve);
    };
    elDialogConflitRecharger.onclick = function () {
      fermerDialogue();
      ouvrirEntree(courante.index);
    };
  }

  // --- Validation -----------------------------------------------------------------------------

  function validerFiche() {
    if (elBoutonValider.disabled || !courante) {
      return;
    }
    annulerAntiRebond();
    var finirValidation = function () {
      window.WaveAudit.envoyer("/lots/" + encodeURIComponent(idLot) + "/entrees/" + courante.index + "/validation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: courante.version }),
      })
        .then(function (reponse) {
          return reponse.json().then(function (corps) {
            return { reponse: reponse, corps: corps };
          });
        })
        .then(function (resultat) {
          if (resultat.reponse.status === 409 && resultat.corps.code === "conflit_version") {
            ouvrirDialogueConflit(resultat.corps.entree, corpsCourant());
            return;
          }
          if (!resultat.reponse.ok) {
            afficherErreur(resultat.corps.detail || "La validation a échoué.");
            return;
          }
          courante = resultat.corps.entree;
          majLigneTiroir(courante);
          elIndicateur.textContent = "Enregistré";
        });
    };
    if (enVol || minuteurAntiRebond) {
      annulerAntiRebond();
      demarrerEnregistrement();
      setTimeout(finirValidation, 0);
    } else {
      finirValidation();
    }
  }

  elBoutonValider.addEventListener("click", validerFiche);
  elBoutonSuivante.addEventListener("click", function () {
    naviguer(1);
  });
  elBoutonPrecedente.addEventListener("click", function () {
    naviguer(-1);
  });

  function naviguer(sens) {
    if (!entrees.length) {
      return;
    }
    var positions = entrees.map(function (e) {
      return e.index;
    });
    var rang = positions.indexOf(focalIndex);
    var suivant = positions[Math.min(Math.max(rang + sens, 0), positions.length - 1)];
    selectionner(suivant);
    ouvrirEntree(suivant);
  }

  // --- Changement de candidat --------------------------------------------------------------

  function demanderCandidat(constatId) {
    var corrigee = courante.fiche_corrigee !== null;
    var validee = courante.statut_relecture === "validee";
    if (corrigee || validee) {
      ouvrirDialogue(elDialogCandidat, elDialogCandidatAnnuler);
      elDialogCandidatConfirmer.onclick = function () {
        fermerDialogue();
        lancerCandidat(constatId, true);
      };
    } else {
      lancerCandidat(constatId, false);
    }
  }

  function lancerCandidat(constatId, confirmer) {
    annulerAntiRebond();
    var envoyer = function (corpsRestant) {
      window.WaveAudit.envoyer("/lots/" + encodeURIComponent(idLot) + "/entrees/" + courante.index + "/candidat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: courante.version, constat_id: constatId, confirmer: confirmer }),
      })
        .then(function (reponse) {
          return reponse.json().then(function (corps) {
            return { reponse: reponse, corps: corps };
          });
        })
        .then(function (resultat) {
          if (resultat.reponse.status === 409 && resultat.corps.code === "confirmation_requise") {
            lancerCandidat(constatId, true);
            return;
          }
          if (resultat.reponse.status === 409 && resultat.corps.code === "conflit_version") {
            courante = resultat.corps.entree;
            afficherErreur("Cette fiche a été modifiée dans un autre onglet. Rechargement.");
            ouvrirEntree(courante.index);
            return;
          }
          if (!resultat.reponse.ok) {
            afficherErreur(resultat.corps.detail || "Le changement de constat a échoué.");
            return;
          }
          courante = resultat.corps.entree;
          ouvrirEntree(courante.index);
        });
    };
    if (enVol) {
      var corps = pendingBody || corpsCourant();
      pendingBody = null;
      envoyerCorrection(corps);
      setTimeout(function () {
        envoyer();
      }, 0);
    } else {
      envoyer();
    }
  }

  // --- Export -----------------------------------------------------------------------------

  function exporterLot(mode) {
    window.WaveAudit.envoyer("/lots/" + encodeURIComponent(idLot) + "/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: mode }),
    }).then(function (reponse) {
      if (!reponse.ok) {
        return window.WaveAudit.messageErreur(reponse).then(function (message) {
          afficherErreur(message);
        });
      }
      return reponse.blob().then(function (blob) {
        var url = URL.createObjectURL(blob);
        var lien = document.createElement("a");
        lien.href = url;
        lien.download = (mode === "final" ? "rapport-" : "brouillon-") + idLot + ".docx";
        document.body.appendChild(lien);
        lien.click();
        lien.remove();
        URL.revokeObjectURL(url);
      });
    });
  }

  elBoutonExportFinal.addEventListener("click", function () {
    if (nonValidees > 0) {
      elDialogExportTexte.textContent =
        nonValidees +
        " fiches ne sont pas validées. Elles seront exclues du rapport et listées en annexe " +
        "comme « non validée ». Exporter quand même ?";
      ouvrirDialogue(elDialogExport, elDialogExportAnnuler);
      elDialogExportConfirmer.onclick = function () {
        fermerDialogue();
        exporterLot("final");
      };
    } else {
      exporterLot("final");
    }
  });
  elBoutonExportBrouillon.addEventListener("click", function () {
    exporterLot("brouillon");
  });

  // --- Dialogues (Échap, focus initial sur « annuler », retour du focus) ---------------------

  function ouvrirDialogue(element, focalInitial) {
    elementAvantDialogue = document.activeElement;
    dialogueOuvert = element;
    element.hidden = false;
    focalInitial.focus();
  }

  function fermerDialogue() {
    if (dialogueOuvert) {
      dialogueOuvert.hidden = true;
      dialogueOuvert = null;
    }
    if (elementAvantDialogue && typeof elementAvantDialogue.focus === "function") {
      elementAvantDialogue.focus();
    }
  }

  document.addEventListener("keydown", function (evenement) {
    if (evenement.key === "Escape" && dialogueOuvert) {
      fermerDialogue();
      return;
    }
    var focusDansChamp = ["INPUT", "TEXTAREA", "SELECT"].indexOf(
      (document.activeElement || {}).tagName
    ) !== -1;
    if (evenement.ctrlKey && !evenement.altKey && evenement.key === "Enter") {
      evenement.preventDefault();
      validerFiche();
      return;
    }
    if (evenement.ctrlKey && evenement.altKey && !focusDansChamp) {
      if (evenement.key === "ArrowDown") {
        evenement.preventDefault();
        naviguer(1);
      } else if (evenement.key === "ArrowUp") {
        evenement.preventDefault();
        naviguer(-1);
      }
    }
  });

  [elDialogCandidatAnnuler, elDialogExportAnnuler].forEach(function (bouton) {
    bouton.addEventListener("click", fermerDialogue);
  });

  function afficherErreur(message) {
    elErreur.hidden = false;
    elErreur.textContent = message;
  }

  interrogerSuivi();
})();
