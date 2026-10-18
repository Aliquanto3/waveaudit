// Harnais de relecture.js (revue W3b) : DOM minimal, minuteries et réseau simulés, faux serveur
// W3a. Lancé par tests/unitaires/test_relecture_js.py seulement si `node` est présent (jamais exigé
// en CI) : node harnais_relecture.js <relecture.js> <cvss_attendus.json>.
"use strict";
const fs = require("fs");
const vm = require("vm");
const assert = require("assert");

const SRC = process.argv[2];

function creerMonde() {
  const ids = {};
  let actif = null;
  class El {
    constructor(tag, id, attrs) {
      this.tagName = tag.toUpperCase();
      this.attrs = Object.assign({}, attrs || {});
      this.children = [];
      this.parent = null;
      this.listeners = {};
      this.hidden = !!(attrs && "hidden" in attrs);
      this.value = "";
      this.disabled = false;
      this._text = "";
      this.className = "";
      this.classList = {
        set: new Set(),
        toggle(c) {
          if (this.set.has(c)) { this.set.delete(c); return false; }
          this.set.add(c); return true;
        },
      };
      if (id) { this.id = id; ids[id] = this; }
    }
    set id(v) { this._id = v; ids[v] = this; }
    get id() { return this._id; }
    set textContent(v) { this._text = String(v); if (v === "") { this.children = []; } }
    get textContent() { return this._text + this.children.map((c) => c.textContent).join(""); }
    set innerHTML(v) { this.children = []; this._text = ""; }
    setAttribute(k, v) { this.attrs[k] = String(v); }
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
    hasAttribute(k) { return k in this.attrs; }
    removeAttribute(k) { delete this.attrs[k]; }
    addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); }
    dispatch(t, ev) { (this.listeners[t] || []).forEach((f) => f(ev || { preventDefault() {}, key: "" })); }
    click() { if (!this.disabled) { this.dispatch("click"); if (this.onclick) this.onclick(); } }
    appendChild(c) { c.parent = this; this.children.push(c); return c; }
    remove() { if (this.parent) { this.parent.children = this.parent.children.filter((x) => x !== this); } }
    focus() { actif = this; }
    descendants() { return this.children.flatMap((c) => [c, ...c.descendants()]); }
    querySelectorAll(sel) {
      const exclu = (sel.match(/:not\(#([\w-]+)\)/) || [])[1];
      return this.descendants().filter((d) => {
        if (exclu && d.id === exclu) return false;
        if (sel.includes('role="option"')) return d.attrs.role === "option";
        if (sel.includes('role="tab"')) return d.attrs.role === "tab";
        if (sel === "button") return d.tagName === "BUTTON";
        return false;
      });
    }
  }
  function el(tag, id, attrs, parent) {
    const e = new El(tag, id, attrs);
    if (parent) parent.appendChild(e);
    return e;
  }
  const body = el("body");
  [
    "etat-texte", "evenements", "telechargement", "relecture-erreur", "tiroir-conteneur",
    "tiroir-bascule", "panneau-note", "note-corps", "catalogue-zone", "catalogue-filtre",
    "panneau-fiche", "generation-en-cours", "motifs", "motifs-liste", "formulaire-fiche",
    "cvss-pastille", "cvss-erreur", "references-liste", "indicateur-enregistrement",
    "bouton-precedente", "bouton-suivante", "bouton-valider", "raison-validation",
    "bouton-exporter-final", "bouton-exporter-brouillon", "dialog-candidat-texte",
    "dialog-export-texte",
  ].forEach((id) => el(id.startsWith("bouton") ? "button" : "div", id, {}, body));
  el("a", "lien-rapport", { hidden: "" }, body);
  el("section", "relecture", { hidden: "" }, body);
  ["champ-titre", "champ-cvss"].forEach((id) => el("input", id, {}, body));
  ["champ-description", "champ-impact", "champ-recommandation"].forEach((id) => el("textarea", id, {}, body));
  el("ul", "tiroir-liste", {}, body);
  el("li", "tiroir-exemple", { role: "option", hidden: "" }, ids["tiroir-liste"]);
  el("ul", "catalogue-liste", {}, body);
  el("li", "catalogue-exemple", { role: "option", hidden: "" }, ids["catalogue-liste"]);
  const barre = el("div", "candidats-barre", { role: "tablist" }, body);
  [1, 2, 3].forEach((r) => el("button", "onglet-candidat-" + r, { role: "tab" }, barre));
  for (const d of ["candidat", "conflit", "export"]) {
    const dlg = el("div", "dialog-" + d, { hidden: "" }, body);
    const btns = d === "conflit" ? ["garder", "recharger"] : ["annuler", "confirmer"];
    btns.forEach((b) => el("button", "dialog-" + d + "-" + b, {}, dlg));
  }

  // Minuteries simulées.
  let maintenant = 0;
  let minuteries = [];
  let seq = 0;
  function setTimeout_(f, ms) { const id = ++seq; minuteries.push({ id, t: maintenant + (ms || 0), f }); return id; }
  function clearTimeout_(id) { minuteries = minuteries.filter((m) => m.id !== id); }

  // Réseau simulé : chaque requête attend `repondre()`.
  const enAttente = [];
  const journal = [];
  function fetch_(url, options) {
    const methode = (options && options.method) || "GET";
    const corps = options && options.body ? JSON.parse(options.body) : null;
    journal.push({ methode, url, corps });
    return new Promise((resolve, reject) => enAttente.push({ methode, url, corps, resolve, reject }));
  }
  function reponse(statut, corps) {
    return {
      status: statut, ok: statut >= 200 && statut < 300,
      json: () => Promise.resolve(corps),
      blob: () => Promise.resolve({}),
    };
  }

  const document = {
    currentScript: { getAttribute: () => "lot1" },
    getElementById: (id) => ids[id] || null,
    createElement: (tag) => new El(tag),
    addEventListener: (t, f) => { (document._l[t] = document._l[t] || []).push(f); },
    _l: {},
    querySelectorAll: (sel) => body.querySelectorAll(sel),
    get activeElement() { return actif; },
    body,
  };
  const window = {};
  window.WaveAudit = {
    envoyer: (url, options) => fetch_(url, options),
    messageErreur: (r) => r.json().then((c) => c.detail),
    MESSAGE_REDEMARRAGE: "redemarrage",
  };
  const contexte = {
    window, document, fetch: fetch_, setTimeout: setTimeout_, clearTimeout: clearTimeout_,
    URL: { createObjectURL: () => "blob:x", revokeObjectURL() {} }, Object, Array, JSON, Math, Number, String, Promise, console,
  };
  vm.createContext(contexte);
  vm.runInContext(fs.readFileSync(SRC, "utf8"), contexte);

  async function vider() { for (let i = 0; i < 20; i += 1) await Promise.resolve(); }
  async function avancer(ms) {
    const fin = maintenant + ms;
    for (;;) {
      minuteries.sort((a, b) => a.t - b.t);
      const m = minuteries[0];
      if (!m || m.t > fin) break;
      minuteries.shift();
      maintenant = m.t;
      m.f();
      await vider();
    }
    maintenant = fin;
    await vider();
  }
  async function repondre(fn) {
    // Répond à la plus ancienne requête : fn(requete) → [statut, corps].
    const r = enAttente.shift();
    assert(r, "aucune requête en attente");
    const [statut, corps] = fn(r);
    if (statut === "reseau") r.reject(new Error("réseau")); else r.resolve(reponse(statut, corps));
    await vider();
    return r;
  }
  function taper(id, valeur) { ids[id].value = valeur; ids[id].dispatch("input"); }
  function touche(cible, key, extra) {
    const ev = Object.assign({ key, preventDefault() {}, ctrlKey: false, altKey: false, shiftKey: false }, extra || {});
    if (cible === "document") (document._l.keydown || []).forEach((f) => f(ev));
    else ids[cible].dispatch("keydown", ev);
  }
  return { ids, enAttente, journal, avancer, repondre, vider, taper, touche, document };
}

// --- Faux serveur W3a -------------------------------------------------------------------------
const GEN_REFS = [{ id: "R1", titre: "Ref 1", url: "" }, { id: "R2", titre: "Ref 2", url: "" }];
function ficheGen(n) {
  return {
    titre: "Titre " + n, description: "D", impact: "I", recommandation: "R",
    cvss: { vecteur: "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N", score: 5.3, severite: "moyenne" },
    references: GEN_REFS, motifs: [],
  };
}
function serveur(n) {
  const entrees = [];
  for (let i = 1; i <= n; i += 1) {
    entrees.push({
      index: i, note: "n" + i + ".md", source: { corps: "corps " + i }, etat: "fiche",
      candidats: [{ id: "C1", score: 1 }, { id: "C2", score: 0.5 }], candidat_choisi: "C1",
      fiche_generee: ficheGen(i), fiche_corrigee: null, ecartee: null, statut_relecture: "a_valider",
      generation: "aucune", erreur_generation: null, version: 1,
    });
  }
  const cle = (e) => JSON.stringify([e.fiche_corrigee, e.statut_relecture]);
  function courante(e) {
    const c = e.fiche_corrigee;
    if (!c) return e.fiche_generee;
    return Object.assign({}, e.fiche_generee, c, { cvss: c.cvss || e.fiche_generee.cvss });
  }
  function traiter(r) {
    const m = r.url.match(/\/entrees\/(\d+)(\/\w+)?/);
    if (r.url.endsWith("/relecture")) {
      return [200, { langue: "fr", non_validees: entrees.filter((e) => e.statut_relecture === "a_valider").length,
        entrees: entrees.map((e) => ({ index: e.index, note: e.note, etat: e.etat, statut_relecture: e.statut_relecture,
          generation: e.generation, version: e.version, titre: courante(e).titre })) }];
    }
    if (r.url.includes("/etat")) return [200, { etat: "termine", evenements: [] }];
    if (r.url.endsWith("/export")) return [200, {}];
    const e = entrees[Number(m[1]) - 1];
    const action = m[2];
    if (!action) {
      return [200, { entree: JSON.parse(JSON.stringify(e)), fiche_courante: courante(e),
        candidats_detail: [{ id: "C1", score: 1, titre: "C1" }, { id: "C2", score: 0.5, titre: "C2" }],
        generable: true, modifiable: true }];
    }
    if (r.corps.version !== e.version) return [409, { code: "conflit_version", detail: "conflit", entree: JSON.parse(JSON.stringify(e)) }];
    const avant = cle(e);
    if (action === "/correction") {
      if (r.corps.titre.length > 50) return [422, { code: "rubrique_trop_longue", detail: "Une rubrique dépasse 50 caractères." }];
      const valide = r.corps.cvss_vecteur.split("/").length === 9;
      e.fiche_corrigee = { titre: r.corps.titre, description: r.corps.description, impact: r.corps.impact,
        recommandation: r.corps.recommandation, cvss_vecteur: r.corps.cvss_vecteur,
        cvss: valide ? { vecteur: r.corps.cvss_vecteur } : null,
        references: GEN_REFS.filter((x) => r.corps.references.includes(x.id)) };
      e.statut_relecture = "a_valider";
    } else if (action === "/validation") {
      e.statut_relecture = "validee";
    } else if (action === "/candidat") {
      if ((e.fiche_corrigee || e.statut_relecture === "validee") && !r.corps.confirmer) {
        return [409, { code: "confirmation_requise", detail: "confirmer" }];
      }
      e.fiche_corrigee = null; e.statut_relecture = "a_valider"; e.candidat_choisi = r.corps.constat_id;
      e.version += 1;
      return [202, { entree: JSON.parse(JSON.stringify(e)) }];
    }
    if (cle(e) !== avant) e.version += 1;
    return [200, { entree: JSON.parse(JSON.stringify(e)) }];
  }
  return { entrees, traiter };
}

async function demarrer(n) {
  const monde = creerMonde();
  const srv = serveur(n || 3);
  monde.srv = srv;
  monde.tout = async () => { while (monde.enAttente.length) await monde.repondre(srv.traiter); };
  await monde.tout(); // etat, relecture, entree 1
  await monde.tout();
  await monde.tout();
  return monde;
}

const tests = {};

tests["cvss : score exact sur des vecteurs connus"] = async () => {
  const m = await demarrer(1);
  const cas = [
    ["CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", "9.8 Critique"],
    ["CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H", "10.0 Critique"],
    ["CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N", "5.3 Moyenne"],
    ["CVSS:3.1/AV:L/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N", "1.8 Faible"],
    ["CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:L/I:L/A:N", "6.4 Moyenne"],
    ["CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N", "0.0 Aucune"],
    ["CVSS:3.1/C:H/I:H/A:H/AV:N/AC:L/PR:N/UI:N/S:U", "9.8 Critique"],
  ];
  for (const [v, attendu] of cas) {
    m.taper("champ-cvss", v);
    assert.strictEqual(m.ids["cvss-pastille"].textContent, attendu, v);
    assert.strictEqual(m.ids["champ-cvss"].getAttribute("aria-invalid"), "false");
  }
  m.taper("champ-cvss", "CVSS:3.1/AV:N");
  assert.strictEqual(m.ids["champ-cvss"].getAttribute("aria-invalid"), "true");
  assert.strictEqual(m.ids["bouton-valider"].disabled, true);
};

tests["1/3 : saisie sur A puis navigation : le PUT part vers A, B intact"] = async () => {
  const m = await demarrer(3);
  m.taper("champ-titre", "A modifié");
  m.ids["bouton-suivante"].click(); // avant 800 ms
  await m.vider();
  const put = m.journal.find((r) => r.methode === "PUT");
  assert(put && put.url.endsWith("/entrees/1/correction"), "PUT vers A envoyé tout de suite");
  assert.strictEqual(put.corps.titre, "A modifié");
  // GET B répondu avant le PUT A
  const getB = m.enAttente.findIndex((r) => r.methode === "GET");
  const [r] = m.enAttente.splice(getB, 1);
  r.resolve({ status: 200, ok: true, json: () => Promise.resolve(m.srv.traiter(r)[1]) });
  await m.vider();
  assert.strictEqual(m.ids["champ-titre"].value, "Titre 2");
  await m.tout(); // PUT A répond maintenant
  assert.strictEqual(m.ids["champ-titre"].value, "Titre 2", "réponse de A n'écrase pas l'écran de B");
  m.taper("champ-titre", "B modifié");
  await m.avancer(800);
  const put2 = m.journal.filter((x) => x.methode === "PUT")[1];
  assert(put2.url.endsWith("/entrees/2/correction"), put2.url);
  assert.strictEqual(put2.corps.version, 1);
  await m.tout();
  assert.strictEqual(m.srv.entrees[0].fiche_corrigee.titre, "A modifié");
  assert.strictEqual(m.srv.entrees[1].fiche_corrigee.titre, "B modifié");
};

tests["1 : Valider sur B pendant un PUT de A en vol vise B"] = async () => {
  const m = await demarrer(3);
  m.taper("champ-titre", "A1");
  await m.avancer(800); // PUT A en vol
  m.ids["bouton-suivante"].click();
  await m.vider();
  const getB = m.enAttente.findIndex((r) => r.methode === "GET");
  const [r] = m.enAttente.splice(getB, 1);
  r.resolve({ status: 200, ok: true, json: () => Promise.resolve(m.srv.traiter(r)[1]) });
  await m.vider();
  m.ids["bouton-valider"].click();
  await m.vider();
  await m.tout();
  await m.tout();
  assert.strictEqual(m.srv.entrees[1].statut_relecture, "validee");
  assert.strictEqual(m.srv.entrees[0].statut_relecture, "a_valider");
  assert(!m.journal.some((x) => x.url.endsWith("/entrees/1/validation")));
};

tests["2 : 422 affiche detail, pas de réessai"] = async () => {
  const m = await demarrer(1);
  m.taper("champ-titre", "x".repeat(60));
  await m.avancer(800);
  await m.tout();
  assert.strictEqual(m.ids["indicateur-enregistrement"].textContent, "Une rubrique dépasse 50 caractères.");
  await m.avancer(10000);
  assert.strictEqual(m.journal.filter((x) => x.methode === "PUT").length, 1);
  // une saisie corrigée repart
  m.taper("champ-titre", "court");
  await m.avancer(800);
  await m.tout();
  assert.strictEqual(m.srv.entrees[0].fiche_corrigee.titre, "court");
  assert.strictEqual(m.ids["indicateur-enregistrement"].textContent, "Enregistré");
};

tests["8 : 503 puis réessai avec le dernier corps"] = async () => {
  const m = await demarrer(1);
  m.taper("champ-titre", "v1");
  await m.avancer(800);
  await m.repondre(() => [503, { code: "ecriture_impossible", detail: "x" }]);
  m.taper("champ-titre", "v2");
  await m.avancer(800); // pendant l'attente du réessai : pas d'envoi
  assert.strictEqual(m.enAttente.length, 0);
  await m.avancer(3000);
  assert.strictEqual(m.enAttente[0].corps.titre, "v2");
  await m.repondre(() => ["reseau"]);
  await m.avancer(3000);
  await m.tout();
  assert.strictEqual(m.srv.entrees[0].fiche_corrigee.titre, "v2");
  assert.strictEqual(m.journal.filter((x) => x.methode === "PUT").length, 3);
};

tests["8 : réessai borné"] = async () => {
  const m = await demarrer(1);
  m.taper("champ-titre", "v1");
  await m.avancer(800);
  for (let i = 0; i < 15; i += 1) {
    if (m.enAttente.length) await m.repondre(() => ["reseau"]);
    await m.avancer(3000);
  }
  assert.strictEqual(m.journal.filter((x) => x.methode === "PUT").length, 11);
  assert(m.ids["indicateur-enregistrement"].textContent.includes("modifiez un champ"));
};

tests["4 : Valider pendant un PUT en vol utilise la version à jour"] = async () => {
  const m = await demarrer(1);
  m.taper("champ-titre", "v1");
  await m.avancer(800); // PUT en vol (version 1)
  m.taper("champ-titre", "v2");
  m.ids["bouton-valider"].click(); // vide l'anti-rebond (v2 en file) puis attend
  await m.vider();
  await m.tout();
  await m.tout();
  await m.tout();
  const val = m.journal.find((x) => x.url.endsWith("/validation"));
  assert.strictEqual(val.corps.version, 3);
  assert.strictEqual(m.srv.entrees[0].statut_relecture, "validee");
  assert.strictEqual(m.srv.entrees[0].fiche_corrigee.titre, "v2");
  assert.strictEqual(m.ids["dialog-conflit"].hidden, true);
};

tests["3 : changement de candidat juste après une frappe : saisie envoyée puis confirmation"] = async () => {
  const m = await demarrer(1);
  m.taper("champ-titre", "corrigé");
  m.ids["onglet-candidat-2"].click();
  await m.vider();
  await m.tout(); // PUT
  assert.strictEqual(m.srv.entrees[0].fiche_corrigee.titre, "corrigé");
  assert.strictEqual(m.ids["dialog-candidat"].hidden, false, "confirmation demandée");
  assert(!m.journal.some((x) => x.url.endsWith("/candidat")));
  m.ids["dialog-candidat-confirmer"].click();
  await m.vider();
  const c = m.enAttente[0];
  assert.strictEqual(c.corps.version, 2);
  assert.strictEqual(c.corps.confirmer, true);
};

tests["confirmation_requise du serveur → dialogue, jamais d'office"] = async () => {
  const m = await demarrer(1);
  m.srv.entrees[0].statut_relecture = "validee"; // écran pas au courant
  m.ids["onglet-candidat-2"].click();
  await m.vider();
  await m.tout();
  assert.strictEqual(m.journal.filter((x) => x.url.endsWith("/candidat")).length, 1);
  assert.strictEqual(m.ids["dialog-candidat"].hidden, false);
};

tests["7 : conflit, Échap puis saisie → dialogue revient, aucun écrasement"] = async () => {
  const m = await demarrer(1);
  m.srv.entrees[0].version = 5; m.srv.entrees[0].fiche_corrigee = { titre: "autre onglet", description: "D", impact: "I", recommandation: "R", cvss_vecteur: "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N", cvss: {}, references: [] };
  m.taper("champ-titre", "moi");
  await m.avancer(800);
  await m.tout();
  assert.strictEqual(m.ids["dialog-conflit"].hidden, false);
  m.touche("document", "Escape");
  assert.strictEqual(m.ids["dialog-conflit"].hidden, true);
  m.taper("champ-titre", "moi encore");
  await m.avancer(800);
  assert.strictEqual(m.enAttente.length, 0, "aucun PUT");
  assert.strictEqual(m.ids["dialog-conflit"].hidden, false);
  assert.strictEqual(m.srv.entrees[0].fiche_corrigee.titre, "autre onglet");
  m.ids["dialog-conflit-garder"].click();
  await m.vider();
  assert.strictEqual(m.enAttente[0].corps.titre, "moi encore");
  assert.strictEqual(m.enAttente[0].corps.version, 5);
  await m.tout();
  assert.strictEqual(m.srv.entrees[0].fiche_corrigee.titre, "moi encore");
};

tests["conflit → Recharger remet la version serveur"] = async () => {
  const m = await demarrer(1);
  m.srv.entrees[0].version = 5;
  m.taper("champ-titre", "moi");
  await m.avancer(800);
  await m.tout();
  m.ids["dialog-conflit-recharger"].click();
  await m.vider();
  await m.tout();
  assert.strictEqual(m.ids["champ-titre"].value, "Titre 1");
  m.taper("champ-titre", "apres");
  await m.avancer(800);
  assert.strictEqual(m.enAttente[0].corps.version, 5);
};

tests["5 : export final relit le compte"] = async () => {
  const m = await demarrer(2);
  m.srv.entrees[0].statut_relecture = "validee";
  m.srv.entrees[1].statut_relecture = "validee";
  m.ids["bouton-exporter-final"].click();
  await m.vider();
  await m.tout();
  await m.tout();
  assert.strictEqual(m.ids["dialog-export"].hidden, true);
  assert(m.journal.some((x) => x.url.endsWith("/export")));
};

tests["5 : export attend la saisie en cours"] = async () => {
  const m = await demarrer(1);
  m.taper("champ-titre", "dernier mot");
  m.ids["bouton-exporter-brouillon"].click();
  await m.vider();
  assert.strictEqual(m.enAttente[0].methode, "PUT");
  await m.tout();
  await m.tout();
  const idxPut = m.journal.findIndex((x) => x.methode === "PUT");
  const idxExp = m.journal.findIndex((x) => x.url.endsWith("/export"));
  assert(idxExp > idxPut);
};

tests["6 : vecteur corrigé invalide relu tel quel"] = async () => {
  const m = await demarrer(2);
  m.taper("champ-cvss", "CVSS:3.1/AV:N/AC:L/PR:N/UI:N");
  await m.avancer(800);
  await m.tout();
  m.ids["bouton-suivante"].click(); await m.vider(); await m.tout();
  m.ids["bouton-precedente"].click(); await m.vider(); await m.tout();
  assert.strictEqual(m.ids["champ-cvss"].value, "CVSS:3.1/AV:N/AC:L/PR:N/UI:N");
  assert.strictEqual(m.ids["champ-cvss"].getAttribute("aria-invalid"), "true");
  assert.strictEqual(m.ids["bouton-valider"].disabled, true);
};

tests["réponses GET dans le désordre : la dernière demandée gagne"] = async () => {
  const m = await demarrer(3);
  m.ids["bouton-suivante"].click(); await m.vider();
  m.ids["bouton-suivante"].click(); await m.vider();
  // répondre d'abord à la 2e (entrée 3) puis à la 1re (entrée 2)
  const [r1, r2] = m.enAttente.splice(0, 2);
  r2.resolve({ status: 200, ok: true, json: () => Promise.resolve(m.srv.traiter(r2)[1]) });
  await m.vider();
  r1.resolve({ status: 200, ok: true, json: () => Promise.resolve(m.srv.traiter(r1)[1]) });
  await m.vider();
  assert.strictEqual(m.ids["champ-titre"].value, "Titre 3");
};

tests["12 : lien du rapport affiché sur lot terminé"] = async () => {
  const m = await demarrer(1);
  assert.strictEqual(m.ids["lien-rapport"].hidden, false);
};

tests["11 : Tab piégé dans le dialogue, Échap rend le focus"] = async () => {
  const m = await demarrer(2);
  m.srv.entrees[0].statut_relecture = "validee";
  await m.tout();
  m.ids["bouton-exporter-final"].focus();
  m.ids["bouton-exporter-final"].click(); await m.vider(); await m.tout();
  assert.strictEqual(m.ids["dialog-export"].hidden, false);
  assert.strictEqual(m.document.activeElement, m.ids["dialog-export-annuler"]);
  m.touche("document", "Tab");
  assert.strictEqual(m.document.activeElement, m.ids["dialog-export-confirmer"]);
  m.touche("document", "Tab");
  assert.strictEqual(m.document.activeElement, m.ids["dialog-export-annuler"]);
  m.touche("document", "Escape");
  assert.strictEqual(m.document.activeElement, m.ids["bouton-exporter-final"]);
};

tests["cvss : les 2592 vecteurs de base égaux au domaine Python"] = async () => {
  const m = await demarrer(1);
  const attendus = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
  const ecarts = [];
  for (const [v, attendu] of attendus) {
    m.taper("champ-cvss", v);
    if (m.ids["cvss-pastille"].textContent !== attendu) ecarts.push(v + " " + m.ids["cvss-pastille"].textContent + " ≠ " + attendu);
  }
  assert.deepStrictEqual(ecarts.slice(0, 5), []);
};

(async () => {
  let echecs = 0;
  for (const [nom, f] of Object.entries(tests)) {
    try { await f(); console.log("ok   " + nom); } catch (e) { echecs += 1; console.log("FAIL " + nom + "\n     " + (e && e.stack ? e.stack.split("\n").slice(0, 3).join("\n     ") : e)); }
  }
  console.log(echecs ? echecs + " échec(s)" : "tout vert");
  process.exit(echecs ? 1 : 0);
})();
