// Écran de relecture d'un lot (contrats §25, §26 ; EXPERIENCE.md « Relecture »). Reprend le
// suivi (barre/journal, lien du rapport v0.1.0) puis bascule sur la relecture (tiroir,
// candidats ou catalogue, fiche, export) dès que le lot n'est plus en_cours.
//
// [revue W3b] Enregistrement : un état par entrée (`etatDe(index)` : version, envoi en vol,
// dernier corps en file, réessai, conflit). Chaque envoi fige l'index et la version de SON
// entrée ; la réponse ne touche l'écran que si cette entrée est encore affichée. La saisie en
// attente d'anti-rebond est envoyée avant tout changement d'entrée ou de candidat, la
// validation, le changement de candidat et l'export attendent la fin de la file. Réessai après
// 3 s sur 503 et erreur réseau seulement (borné, avec le dernier corps saisi) ; tout autre refus
// affiche son `detail` et s'arrête ; 409 conflit_version → dialogue (Échap ne vaut pas choix).
(function () {
  "use strict";

  var script = document.currentScript;
  var idLot = script.getAttribute("data-id-lot");
  var baseLot = "/lots/" + encodeURIComponent(idLot);

  var elEtatTexte = document.getElementById("etat-texte");
  var elEvenements = document.getElementById("evenements");
  var elLienRapport = document.getElementById("lien-rapport");

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
  var elDialogCandidatAnnuler = document.getElementById("dialog-candidat-annuler");
  var elDialogCandidatConfirmer = document.getElementById("dialog-candidat-confirmer");

  var elDialogConflit = document.getElementById("dialog-conflit");
  var elDialogConflitGarder = document.getElementById("dialog-conflit-garder");
  var elDialogConflitRecharger = document.getElementById("dialog-conflit-recharger");

  var elDialogExport = document.getElementById("dialog-export");
  var elDialogExportTexte = document.getElementById("dialog-export-texte");
  var elDialogExportAnnuler = document.getElementById("dialog-export-annuler");
  var elDialogExportConfirmer = document.getElementById("dialog-export-confirmer");

  var CHAMPS = [elTitre, elDescription, elImpact, elRecommandation, elCvss];
  var ANTI_REBOND_MS = 800;
  var REESSAI_MS = 3000;
  var REESSAIS_MAX = 10;
  var MSG_REESSAI =
    "La correction n'a pas pu être enregistrée. Dernière version conservée à l'écran ; " +
    "nouvelle tentative dans quelques secondes.";
  var MSG_ABANDON =
    "La correction n'a pas pu être enregistrée. Votre saisie reste à l'écran : modifiez un " +
    "champ pour réessayer, ou rechargez la page.";
  var MSG_RESEAU = "Le serveur ne répond pas. Rechargez la page dans un instant.";

  var recus = 0;
  var entrees = []; // résumés de GET /relecture, mis à jour par les réponses d'écriture
  var nonValidees = 0;
  var focalIndex = -1; // ligne sélectionnée dans le tiroir
  var catalogue = null; // chargé une fois, à la demande

  var etats = {}; // index → état d'enregistrement de l'entrée
  var ouverte = null; // état de l'entrée affichée
  var jetonAffichage = 0; // seule la dernière ouverture demandée est rendue
  var ficheCourante = null;
  var candidatsDetail = [];
  var generable = false;
  var modifiable = false;
  var referencesCourantes = [];
  var minuteurGeneration = null;

  var dialogueOuvert = null;
  var elementAvantDialogue = null;

  // --- Outils -------------------------------------------------------------------------------

  function lireReponse(reponse) {
    // Corps JSON d'une réponse (ou {} si illisible), avec le statut.
    return reponse
      .json()
      .catch(function () {
        return {};
      })
      .then(function (corps) {
        return { reponse: reponse, corps: corps || {} };
      });
  }

  function detailDe(resultat, defaut) {
    if (resultat.reponse.redemarrage) {
      return window.WaveAudit.MESSAGE_REDEMARRAGE;
    }
    return resultat.corps.detail || defaut;
  }

  function afficherErreur(message) {
    elErreur.hidden = false;
    elErreur.textContent = message;
  }

  function effacerErreur() {
    elErreur.hidden = true;
    elErreur.textContent = "";
  }

  // --- Suivi --------------------------------------------------------------------------------

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
    fetch(baseLot + "/etat?depuis=" + recus)
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
          elLienRapport.hidden = false; // rapport.docx du lot (W2), inchangé
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

  // --- Relecture : liste --------------------------------------------------------------------

  function afficherRelecture() {
    elRelecture.hidden = false;
    chargerListe(function () {
      if (entrees.length && focalIndex === -1) {
        selectionner(entrees[0].index);
        ouvrirEntree(entrees[0].index);
      }
    });
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

  function compterNonValidees() {
    nonValidees = entrees.filter(function (e) {
      return e.etat === "fiche" && e.statut_relecture === "a_valider";
    }).length;
  }

  function chargerListe(suite) {
    fetch(baseLot + "/relecture")
      .then(lireReponse)
      .then(function (resultat) {
        if (!resultat.reponse.ok) {
          afficherErreur(detailDe(resultat, "La liste des fiches est illisible."));
          return;
        }
        var donnees = resultat.corps;
        entrees = donnees.entrees || [];
        var langue = donnees.langue || "fr";
        nonValidees = donnees.non_validees || 0;
        elPanneauNote.setAttribute("lang", langue);
        elPanneauFiche.setAttribute("lang", langue);
        rendreTiroir();
        if (suite) {
          suite();
        }
      })
      .catch(function () {
        afficherErreur(MSG_RESEAU);
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
      li.id = "tiroir-ligne-" + entree.index;
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
    if (focalIndex !== -1) {
      selectionner(focalIndex);
    }
  }

  function selectionner(index) {
    focalIndex = index;
    Array.prototype.forEach.call(elTiroirListe.querySelectorAll('li[role="option"]'), function (li) {
      li.setAttribute("aria-selected", li.getAttribute("data-index") === String(index) ? "true" : "false");
    });
    if (document.getElementById("tiroir-ligne-" + index)) {
      elTiroirListe.setAttribute("aria-activedescendant", "tiroir-ligne-" + index);
    }
  }

  function majLigneTiroir(entree) {
    // Entrée complète (réponse d'écriture) → résumé de la ligne du tiroir.
    var corrigee = entree.fiche_corrigee;
    var generee = entree.fiche_generee;
    var titre = corrigee ? corrigee.titre : generee ? generee.titre : null;
    entrees = entrees.map(function (e) {
      return e.index === entree.index
        ? Object.assign({}, e, {
            etat: entree.etat,
            statut_relecture: entree.statut_relecture,
            generation: entree.generation,
            version: entree.version,
            titre: entree.etat === "fiche" ? titre : null,
          })
        : e;
    });
    compterNonValidees();
    rendreTiroir();
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
      if (focalIndex !== -1) {
        ouvrirEntree(focalIndex);
      }
    }
  });

  elTiroirBascule.addEventListener("click", function () {
    var repli = elTiroirConteneur.classList.toggle("tiroir-repli");
    elTiroirBascule.setAttribute("aria-expanded", repli ? "false" : "true");
  });

  // --- État d'enregistrement par entrée -------------------------------------------------------

  function etatDe(index) {
    if (!etats[index]) {
      etats[index] = {
        index: index,
        version: null, // dernière version connue du serveur
        entree: null, // dernière entrée complète reçue
        minuteur: null, // anti-rebond en cours
        enVol: false, // une écriture (PUT, validation, candidat) attend sa réponse
        attente: null, // dernier corps saisi, pas encore envoyé
        dernier: null, // dernier corps saisi (envoyé ou non)
        reessai: null, // minuteur de nouvelle tentative (503, réseau)
        essais: 0,
        echec: false, // dernier envoi refusé (422…) : la saisie à l'écran n'est pas sur disque
        conflit: null, // entrée du serveur reçue avec un 409 conflit_version, sans choix
        apres: [], // rappels en attente de la fin de la file
        generation: null, // dernier état de génération rendu (annonce de fin)
      };
    }
    return etats[index];
  }

  function occupe(st) {
    return st.enVol || st.reessai !== null || st.attente !== null || st.minuteur !== null;
  }

  function annoncer(st, message) {
    if (st === ouverte) {
      elIndicateur.textContent = message;
    }
  }

  function planifierEnregistrement() {
    var st = ouverte;
    if (!st || !modifiable || ficheCourante === null) {
      return;
    }
    if (st.minuteur) {
      clearTimeout(st.minuteur);
    }
    st.minuteur = setTimeout(function () {
      st.minuteur = null;
      if (st === ouverte) {
        enfiler(st, corpsCourant());
      }
    }, ANTI_REBOND_MS);
  }

  function vider(st) {
    // Envoie tout de suite la saisie en attente d'anti-rebond (l'écran montre encore `st`).
    if (st && st.minuteur) {
      clearTimeout(st.minuteur);
      st.minuteur = null;
      if (st === ouverte) {
        enfiler(st, corpsCourant());
      }
    }
  }

  function enfiler(st, corps) {
    st.dernier = corps;
    st.attente = corps;
    if (st.conflit) {
      if (st === ouverte) {
        ouvrirDialogueConflit(st);
      }
      return;
    }
    if (!st.enVol && st.reessai === null) {
      envoyerSuivant(st);
    }
  }

  function envoyerSuivant(st) {
    var corps = st.attente;
    st.attente = null;
    envoyerCorrection(st, corps);
  }

  function terminer(st) {
    // Fin d'une écriture : corps suivant en file, sinon rappels de fin de file, un par un (un
    // rappel qui écrit à son tour, une validation par exemple, fait attendre les suivants).
    if (st.attente !== null && !st.conflit) {
      envoyerSuivant(st);
      return;
    }
    while (st.apres.length && !occupe(st) && !st.conflit) {
      st.apres.shift()(!st.echec);
    }
  }

  function apresFile(st, rappel) {
    // `rappel(true)` une fois la file de `st` vide et la dernière saisie enregistrée.
    vider(st);
    if (st.conflit) {
      if (st === ouverte) {
        ouvrirDialogueConflit(st);
      }
      rappel(false);
      return;
    }
    if (occupe(st) || st.apres.length) {
      st.apres.push(rappel);
      return;
    }
    rappel(!st.echec);
  }

  function annulerRappels(st) {
    var rappels = st.apres;
    st.apres = [];
    rappels.forEach(function (rappel) {
      rappel(false);
    });
  }

  function recevoirEntree(st, entree) {
    st.version = entree.version;
    st.entree = entree;
    majLigneTiroir(entree);
  }

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

  function envoyerCorrection(st, corps) {
    st.enVol = true;
    annoncer(st, "Enregistrement…");
    var requete = Object.assign({ version: st.version }, corps);
    window.WaveAudit.envoyer(baseLot + "/entrees/" + st.index + "/correction", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requete),
    })
      .then(lireReponse)
      .then(function (resultat) {
        st.enVol = false;
        var statut = resultat.reponse.status;
        if (statut === 409 && resultat.corps.code === "conflit_version" && resultat.corps.entree) {
          st.conflit = resultat.corps.entree;
          if (st.attente === null) {
            st.attente = corps;
          }
          if (st === ouverte) {
            ouvrirDialogueConflit(st);
          }
          return;
        }
        if (statut === 503) {
          reessayer(st, corps);
          return;
        }
        st.essais = 0;
        if (!resultat.reponse.ok) {
          st.echec = true;
          annoncer(st, detailDe(resultat, "La correction a été refusée."));
          terminer(st);
          return;
        }
        st.echec = false;
        recevoirEntree(st, resultat.corps.entree);
        if (st === ouverte) {
          majBoutonValider();
          if (st.attente === null) {
            elIndicateur.textContent = "Enregistré";
          }
        }
        terminer(st);
      })
      .catch(function () {
        st.enVol = false;
        reessayer(st, corps);
      });
  }

  function reessayer(st, corps) {
    st.essais += 1;
    if (st.attente === null) {
      st.attente = corps; // sinon une saisie plus récente part à la place
    }
    if (st.essais > REESSAIS_MAX) {
      st.essais = 0;
      st.echec = true;
      st.attente = null;
      annoncer(st, MSG_ABANDON);
      terminer(st);
      return;
    }
    annoncer(st, MSG_REESSAI);
    st.reessai = setTimeout(function () {
      st.reessai = null;
      if (st.conflit) {
        return;
      }
      if (st.attente !== null) {
        envoyerSuivant(st);
      } else {
        terminer(st);
      }
    }, REESSAI_MS);
  }

  function ouvrirDialogueConflit(st) {
    ouvrirDialogue(elDialogConflit, elDialogConflitGarder);
    elDialogConflitGarder.onclick = function () {
      fermerDialogue();
      // La version du serveur est reprise ; la saisie à l'écran (la plus récente) est renvoyée.
      var serveur = st.conflit;
      st.conflit = null;
      st.version = serveur.version;
      st.entree = serveur;
      st.attente = st === ouverte ? corpsCourant() : st.attente || st.dernier;
      if (st.attente !== null && !st.enVol && st.reessai === null) {
        envoyerSuivant(st);
      } else {
        terminer(st);
      }
    };
    elDialogConflitRecharger.onclick = function () {
      fermerDialogue();
      st.conflit = null;
      st.attente = null;
      st.dernier = null;
      st.echec = false;
      annulerRappels(st);
      ouvrirEntree(st.index);
    };
  }

  // --- Relecture : une entrée ---------------------------------------------------------------

  function ouvrirEntree(index) {
    vider(ouverte);
    if (minuteurGeneration) {
      clearTimeout(minuteurGeneration);
      minuteurGeneration = null;
    }
    var jeton = ++jetonAffichage;
    fetch(baseLot + "/entrees/" + index)
      .then(lireReponse)
      .then(function (resultat) {
        if (jeton !== jetonAffichage) {
          return; // une autre entrée a été demandée entre-temps
        }
        if (!resultat.reponse.ok) {
          afficherErreur(detailDe(resultat, "Cette fiche est illisible."));
          return;
        }
        effacerErreur();
        rendreEntree(index, resultat.corps);
      })
      .catch(function () {
        if (jeton === jetonAffichage) {
          afficherErreur(MSG_RESEAU);
        }
      });
  }

  function remplirChamps(fiche, corrigee) {
    elTitre.value = fiche.titre;
    elDescription.value = fiche.description;
    elImpact.value = fiche.impact;
    elRecommandation.value = fiche.recommandation;
    // [revue W3b] Vecteur corrigé invalide : `fiche_courante` garde le CVSS généré ; le champ
    // montre la saisie enregistrée telle quelle (et son état invalide), pas le vecteur généré.
    var vecteur = corrigee ? corrigee.cvss_vecteur : fiche.cvss ? fiche.cvss.vecteur : "";
    elCvss.value = vecteur;
    rendreCvss(vecteur);
  }

  function remplirDepuisCorps(corps) {
    elTitre.value = corps.titre;
    elDescription.value = corps.description;
    elImpact.value = corps.impact;
    elRecommandation.value = corps.recommandation;
    elCvss.value = corps.cvss_vecteur;
    rendreCvss(corps.cvss_vecteur);
  }

  function rendreEntree(index, donnees) {
    var st = etatDe(index);
    var entree = donnees.entree;
    if (ouverte && ouverte !== st) {
      vider(ouverte); // frappe dans l'ancienne fiche pendant la lecture de la nouvelle
    }
    var enCours = st.enVol || st.reessai !== null || st.attente !== null || !!st.conflit;
    ouverte = st;
    if (!enCours) {
      // Écriture précédente terminée : la version lue est la bonne. Sinon la réponse de
      // l'écriture en vol la donnera (la lecture peut l'avoir précédée).
      st.version = entree.version;
      st.entree = entree;
      majLigneTiroir(entree);
    }
    ficheCourante = donnees.fiche_courante;
    candidatsDetail = donnees.candidats_detail || [];
    generable = donnees.generable;
    modifiable = donnees.modifiable;

    elNoteCorps.textContent = entree.source ? entree.source.corps : entree.note;

    var nonRattachee =
      entree.etat === "ecartee" && entree.ecartee && entree.ecartee.statut === "non_rattachee";
    elCandidatsBarre.hidden = nonRattachee;
    elCatalogueZone.hidden = !nonRattachee;
    if (nonRattachee) {
      chargerCatalogue();
    } else {
      rendreCandidats(entree);
    }

    var enGeneration = entree.generation === "en_cours";
    if (entree.generation === "echec") {
      elGenerationEnCours.hidden = false;
      elGenerationEnCours.textContent =
        "La régénération a échoué : " + (entree.erreur_generation || "erreur inconnue");
    } else {
      elGenerationEnCours.hidden = !enGeneration;
      elGenerationEnCours.textContent = "Génération en cours…";
    }
    elPanneauFiche.setAttribute("aria-busy", enGeneration ? "true" : "false");

    if (ficheCourante && (enCours || st.echec) && st.dernier) {
      remplirDepuisCorps(st.dernier); // saisie pas (encore) enregistrée : elle reste à l'écran
      rendreReferences(
        ((entree.fiche_generee && entree.fiche_generee.references) || []).filter(function (r) {
          return st.dernier.references.indexOf(r.id) !== -1;
        })
      );
    } else if (ficheCourante) {
      remplirChamps(ficheCourante, entree.fiche_corrigee);
      rendreReferences(ficheCourante.references || []);
    } else {
      CHAMPS.forEach(function (champ) {
        champ.value = "";
      });
      rendreCvss("");
      rendreReferences([]);
    }

    var motifs = entree.fiche_generee && entree.fiche_generee.motifs ? entree.fiche_generee.motifs : [];
    elMotifs.hidden = motifs.length === 0;
    elMotifsListe.textContent = "";
    motifs.forEach(function (motif) {
      var li = document.createElement("li");
      li.textContent = motif.detail + " (signalé à la génération)";
      elMotifsListe.appendChild(li);
    });

    CHAMPS.forEach(function (champ) {
      champ.disabled = ficheCourante === null || !modifiable;
    });
    majBoutonValider();

    if (st.generation === "en_cours" && !enGeneration) {
      elIndicateur.textContent = "Génération terminée.";
    } else if (!enCours) {
      elIndicateur.textContent = "";
    }
    st.generation = entree.generation;

    if (enGeneration) {
      minuteurGeneration = setTimeout(function () {
        minuteurGeneration = null;
        if (ouverte === st) {
          ouvrirEntree(index);
        }
      }, 1000);
    }
    if (st.conflit) {
      ouvrirDialogueConflit(st);
    }
  }

  function majBoutonValider() {
    elBoutonValider.disabled = !modifiable || ficheCourante === null || !cvssValide(elCvss.value);
    elRaisonValidation.hidden = !elBoutonValider.disabled;
  }

  // --- Candidats (APG Tabs, activation manuelle : un onglet relance la génération) ---------

  function ongletsCandidats() {
    return Array.prototype.slice.call(elCandidatsBarre.querySelectorAll('[role="tab"]'));
  }

  function rendreCandidats(entree) {
    var choisi = null;
    var focalisable = null;
    ongletsCandidats().forEach(function (bouton, rang) {
      var detail = candidatsDetail[rang];
      if (detail) {
        bouton.hidden = false;
        bouton.textContent = detail.titre + " (" + Number(detail.score).toFixed(2) + ")";
        bouton.setAttribute("data-constat-id", detail.id);
        var estChoisi = entree.candidat_choisi === detail.id;
        bouton.setAttribute("aria-selected", estChoisi ? "true" : "false");
        bouton.setAttribute("tabindex", "-1");
        bouton.disabled = !generable || estChoisi;
        if (estChoisi) {
          choisi = bouton;
        }
        if (!bouton.disabled && focalisable === null) {
          focalisable = bouton; // l'onglet choisi est désactivé : le premier actif prend Tab
        }
      } else {
        bouton.hidden = true;
        bouton.removeAttribute("data-constat-id");
        bouton.setAttribute("aria-selected", "false");
      }
    });
    if (focalisable) {
      focalisable.setAttribute("tabindex", "0");
    }
    elPanneauFiche.setAttribute("aria-labelledby", (choisi || ongletsCandidats()[0]).id);
  }

  ongletsCandidats().forEach(function (bouton) {
    bouton.addEventListener("click", function () {
      var constatId = bouton.getAttribute("data-constat-id");
      if (constatId) {
        demanderCandidat(constatId);
      }
    });
  });

  elCandidatsBarre.addEventListener("keydown", function (evenement) {
    if (evenement.key !== "ArrowLeft" && evenement.key !== "ArrowRight") {
      return;
    }
    var actifs = ongletsCandidats().filter(function (b) {
      return !b.hidden && !b.disabled;
    });
    if (!actifs.length) {
      return;
    }
    evenement.preventDefault();
    var rang = actifs.indexOf(document.activeElement);
    var pas = evenement.key === "ArrowRight" ? 1 : -1;
    var suivant = actifs[(rang + pas + actifs.length) % actifs.length];
    suivant.focus();
  });

  function chargerCatalogue() {
    if (catalogue !== null) {
      rendreCatalogue();
      return;
    }
    fetch(baseLot + "/catalogue")
      .then(lireReponse)
      .then(function (resultat) {
        if (!resultat.reponse.ok) {
          afficherErreur(detailDe(resultat, "Le catalogue est illisible."));
          return;
        }
        catalogue = resultat.corps.constats || [];
        rendreCatalogue();
      })
      .catch(function () {
        afficherErreur(MSG_RESEAU);
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
    filtrerCatalogue();
  }

  function filtrerCatalogue() {
    var filtre = elCatalogueFiltre.value.trim().toLowerCase();
    Array.prototype.forEach.call(
      elCatalogueListe.querySelectorAll('li[role="option"]:not(#catalogue-exemple)'),
      function (li) {
        li.hidden = filtre !== "" && li.textContent.toLowerCase().indexOf(filtre) === -1;
      }
    );
  }

  elCatalogueFiltre.addEventListener("input", filtrerCatalogue);

  // --- CVSS 3.1 (aperçu local du score de base, jamais envoyé) -------------------------------

  var POIDS = {
    AV: { N: 0.85, A: 0.62, L: 0.55, P: 0.2 },
    AC: { L: 0.77, H: 0.44 },
    UI: { N: 0.85, R: 0.62 },
    CIA: { H: 0.56, L: 0.22, N: 0 },
  };
  var METRIQUES = {
    AV: "NALP",
    AC: "LH",
    PR: "NLH",
    UI: "NR",
    S: "UC",
    C: "NLH",
    I: "NLH",
    A: "NLH",
  };

  function lireVecteur(vecteur) {
    // Les 8 métriques de base, dans n'importe quel ordre (comme domaine/cvss31), sinon null.
    var texte = vecteur || ""; // pas de trim : le serveur évalue la saisie telle quelle
    if (texte.indexOf("CVSS:3.1/") !== 0) {
      return null;
    }
    var valeurs = {};
    var morceaux = texte.slice("CVSS:3.1/".length).split("/");
    for (var i = 0; i < morceaux.length; i += 1) {
      var paire = morceaux[i].split(":");
      var nom = paire[0];
      if (
        paire.length !== 2 ||
        !Object.prototype.hasOwnProperty.call(METRIQUES, nom) ||
        Object.prototype.hasOwnProperty.call(valeurs, nom) ||
        paire[1].length !== 1 ||
        METRIQUES[nom].indexOf(paire[1]) === -1
      ) {
        return null;
      }
      valeurs[nom] = paire[1];
    }
    return Object.keys(valeurs).length === 8 ? valeurs : null;
  }

  function arrondiSuperieur(x) {
    var entier = Math.round(x * 100000);
    if (entier % 10000 === 0) {
      return entier / 100000;
    }
    return (Math.floor(entier / 10000) + 1) / 10;
  }

  function scoreCvss(m) {
    var change = m.S === "C";
    var pr = { N: 0.85, L: change ? 0.68 : 0.62, H: change ? 0.5 : 0.27 }[m.PR];
    var iss = 1 - (1 - POIDS.CIA[m.C]) * (1 - POIDS.CIA[m.I]) * (1 - POIDS.CIA[m.A]);
    var impact = change ? 7.52 * (iss - 0.029) - 3.25 * Math.pow(iss - 0.02, 15) : 6.42 * iss;
    var exploitabilite = 8.22 * POIDS.AV[m.AV] * POIDS.AC[m.AC] * pr * POIDS.UI[m.UI];
    if (impact <= 0) {
      return 0;
    }
    var brut = change ? 1.08 * (impact + exploitabilite) : impact + exploitabilite;
    return arrondiSuperieur(Math.min(brut, 10));
  }

  function severiteDe(score) {
    if (score === 0) {
      return "aucune";
    }
    if (score < 4) {
      return "faible";
    }
    if (score < 7) {
      return "moyenne";
    }
    if (score < 9) {
      return "elevee";
    }
    return "critique";
  }

  function cvssValide(vecteur) {
    return lireVecteur(vecteur) !== null;
  }

  var LIBELLES_SEVERITE = {
    aucune: "Aucune",
    faible: "Faible",
    moyenne: "Moyenne",
    elevee: "Élevée",
    critique: "Critique",
  };

  function rendreCvss(vecteur) {
    var metriques = lireVecteur(vecteur);
    if (metriques) {
      var score = scoreCvss(metriques);
      var severite = severiteDe(score);
      elCvssPastille.className = "severite-" + severite;
      elCvssPastille.textContent = score.toFixed(1) + " " + LIBELLES_SEVERITE[severite];
    } else {
      elCvssPastille.className = "";
      elCvssPastille.textContent = "";
    }
    var invalide = (vecteur || "").trim() !== "" && metriques === null;
    elCvss.setAttribute("aria-invalid", invalide ? "true" : "false");
    elCvssErreur.hidden = !invalide;
  }

  elCvss.addEventListener("input", function () {
    rendreCvss(elCvss.value);
    majBoutonValider();
  });

  // --- Références (sous-ensemble ordonné, retrait seul) --------------------------------------

  function rendreReferences(references) {
    referencesCourantes = references.slice();
    elReferencesListe.textContent = "";
    referencesCourantes.forEach(function (reference) {
      var li = document.createElement("li");
      var texte = document.createElement("span");
      texte.textContent = reference.titre;
      li.appendChild(texte);
      var bouton = document.createElement("button");
      bouton.type = "button";
      bouton.textContent = "Retirer";
      bouton.disabled = !modifiable;
      bouton.setAttribute("aria-label", "Retirer la référence " + reference.titre);
      bouton.addEventListener("click", function () {
        rendreReferences(
          referencesCourantes.filter(function (r) {
            return r.id !== reference.id;
          })
        );
        planifierEnregistrement();
      });
      li.appendChild(bouton);
      elReferencesListe.appendChild(li);
    });
  }

  CHAMPS.forEach(function (champ) {
    champ.addEventListener("input", planifierEnregistrement);
  });

  // --- Validation -----------------------------------------------------------------------------

  function validerFiche() {
    var st = ouverte;
    if (!st || elBoutonValider.disabled) {
      return;
    }
    apresFile(st, function (propre) {
      if (!propre || st !== ouverte || elBoutonValider.disabled) {
        return; // refus déjà affiché, conflit en cours ou autre fiche ouverte
      }
      st.enVol = true;
      window.WaveAudit.envoyer(baseLot + "/entrees/" + st.index + "/validation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: st.version }),
      })
        .then(lireReponse)
        .then(function (resultat) {
          st.enVol = false;
          if (resultat.reponse.status === 409 && resultat.corps.code === "conflit_version") {
            st.conflit = resultat.corps.entree;
            if (st === ouverte) {
              ouvrirDialogueConflit(st);
            }
            return;
          }
          if (!resultat.reponse.ok) {
            annoncer(st, detailDe(resultat, "La validation a échoué."));
          } else {
            recevoirEntree(st, resultat.corps.entree);
            annoncer(st, "Fiche validée.");
          }
          terminer(st);
        })
        .catch(function () {
          st.enVol = false;
          annoncer(st, "La validation n'a pas pu être envoyée. Réessayez dans un instant.");
          terminer(st);
        });
    });
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
    var st = ouverte;
    if (!st) {
      return;
    }
    // La saisie en attente part d'abord ; la décision se prend sur l'entrée enregistrée.
    apresFile(st, function (propre) {
      if (!propre || st !== ouverte) {
        return;
      }
      var entree = st.entree || {};
      if (entree.fiche_corrigee || entree.statut_relecture === "validee") {
        confirmerCandidat(st, constatId);
      } else {
        lancerCandidat(st, constatId, false);
      }
    });
  }

  function confirmerCandidat(st, constatId) {
    ouvrirDialogue(elDialogCandidat, elDialogCandidatAnnuler);
    elDialogCandidatConfirmer.onclick = function () {
      fermerDialogue();
      apresFile(st, function (propre) {
        if (propre && st === ouverte) {
          lancerCandidat(st, constatId, true);
        }
      });
    };
  }

  function lancerCandidat(st, constatId, confirmer) {
    st.enVol = true;
    window.WaveAudit.envoyer(baseLot + "/entrees/" + st.index + "/candidat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version: st.version, constat_id: constatId, confirmer: confirmer }),
    })
      .then(lireReponse)
      .then(function (resultat) {
        st.enVol = false;
        var code = resultat.corps.code;
        if (resultat.reponse.status === 409 && code === "confirmation_requise") {
          // La fiche porte des corrections que l'écran ignorait : on demande, jamais d'office.
          terminer(st);
          if (st === ouverte) {
            confirmerCandidat(st, constatId);
          }
          return;
        }
        if (resultat.reponse.status === 409 && code === "conflit_version") {
          terminer(st);
          afficherErreur("Cette fiche a été modifiée dans un autre onglet. Rechargement.");
          if (st === ouverte) {
            ouvrirEntree(st.index);
          }
          return;
        }
        if (!resultat.reponse.ok) {
          terminer(st);
          afficherErreur(detailDe(resultat, "Le changement de constat a échoué."));
          return;
        }
        recevoirEntree(st, resultat.corps.entree);
        terminer(st);
        if (st === ouverte) {
          ouvrirEntree(st.index); // sondage jusqu'à generation != "en_cours"
        }
      })
      .catch(function () {
        st.enVol = false;
        terminer(st);
        afficherErreur(MSG_RESEAU);
      });
  }

  // --- Export -----------------------------------------------------------------------------

  function exporterLot(mode) {
    window.WaveAudit.envoyer(baseLot + "/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: mode }),
    })
      .then(function (reponse) {
        if (!reponse.ok) {
          return window.WaveAudit.messageErreur(reponse).then(afficherErreur);
        }
        return reponse.blob().then(function (blob) {
          var url = URL.createObjectURL(blob);
          var lien = document.createElement("a");
          lien.href = url;
          lien.download = (mode === "final" ? "rapport-" : "brouillon-") + idLot + ".docx";
          document.body.appendChild(lien);
          lien.click();
          lien.remove();
          setTimeout(function () {
            URL.revokeObjectURL(url);
          }, 1000);
        });
      })
      .catch(function () {
        afficherErreur(MSG_RESEAU);
      });
  }

  function apresSaisies(rappel) {
    // L'export lit le disque : la saisie de la fiche affichée est enregistrée d'abord.
    if (!ouverte) {
      rappel(true);
      return;
    }
    apresFile(ouverte, rappel);
  }

  elBoutonExportFinal.addEventListener("click", function () {
    apresSaisies(function (propre) {
      if (!propre) {
        return;
      }
      // Compte relu au moment de l'export (validations faites dans un autre onglet comprises).
      chargerListe(function () {
        if (nonValidees > 0) {
          elDialogExportTexte.textContent =
            nonValidees +
            (nonValidees > 1 ? " fiches ne sont pas validées." : " fiche n'est pas validée.") +
            " Elles seront exclues du rapport et listées en annexe comme « non validée ». " +
            "Exporter quand même ?";
          ouvrirDialogue(elDialogExport, elDialogExportAnnuler);
          elDialogExportConfirmer.onclick = function () {
            fermerDialogue();
            exporterLot("final");
          };
        } else {
          exporterLot("final");
        }
      });
    });
  });
  elBoutonExportBrouillon.addEventListener("click", function () {
    apresSaisies(function (propre) {
      if (propre) {
        exporterLot("brouillon");
      }
    });
  });

  // --- Dialogues (Échap, focus initial sur « annuler », piège du focus, retour du focus) -----

  function ouvrirDialogue(element, focalInitial) {
    if (dialogueOuvert === element) {
      return;
    }
    if (dialogueOuvert) {
      dialogueOuvert.hidden = true;
    } else {
      elementAvantDialogue = document.activeElement;
    }
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
    elementAvantDialogue = null;
  }

  function pieger(evenement) {
    var boutons = Array.prototype.slice.call(dialogueOuvert.querySelectorAll("button"));
    if (!boutons.length) {
      return;
    }
    var rang = boutons.indexOf(document.activeElement);
    evenement.preventDefault();
    var pas = evenement.shiftKey ? -1 : 1;
    boutons[(rang + pas + boutons.length) % boutons.length].focus();
  }

  document.addEventListener("keydown", function (evenement) {
    if (dialogueOuvert) {
      if (evenement.key === "Escape") {
        // Fermeture sans choix. Pour un conflit, rien n'est écrit : la saisie reste à l'écran
        // et le dialogue revient à la prochaine saisie (jamais d'écrasement silencieux).
        evenement.preventDefault();
        fermerDialogue();
      } else if (evenement.key === "Tab") {
        pieger(evenement);
      }
      return; // aucun raccourci de la page sous un dialogue modal
    }
    var focusDansChamp =
      ["INPUT", "TEXTAREA", "SELECT"].indexOf((document.activeElement || {}).tagName) !== -1;
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

  interrogerSuivi();
})();
