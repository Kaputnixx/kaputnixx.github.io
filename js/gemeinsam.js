// Gemeinsamer Code für alle Seiten: lädt inhalt/seite.json, baut Kopf- und
// Fußzeile, setzt den Seitentitel und füllt die Platzhalterfelder.
// Kein Netz, keine Cookies, kein localStorage: es werden nur Dateien dieser
// Seite gelesen.

const zwischenspeicher = new Map();

/** Lädt eine JSON-Datei dieser Seite (jede nur einmal). */
export function ladeJson(pfad) {
  if (!zwischenspeicher.has(pfad)) {
    zwischenspeicher.set(
      pfad,
      fetch(pfad).then((antwort) => {
        if (!antwort.ok) throw new Error(`${pfad}: ${antwort.status}`);
        return antwort.json();
      }),
    );
  }
  return zwischenspeicher.get(pfad);
}

export const seite = ladeJson("inhalt/seite.json");

export const istPlatzhalter = (text) => typeof text === "string" && text.includes("[HIER EINTRAGEN");

/** Kleine Hilfe zum Bauen von Elementen. Texte werden nie als HTML gelesen. */
export function el(tag, attribute = {}, ...kinder) {
  const knoten = document.createElement(tag);
  for (const [name, wert] of Object.entries(attribute)) {
    if (wert === false || wert == null) continue;
    if (name === "klasse") knoten.className = wert;
    else if (name === "text") knoten.textContent = wert;
    else knoten.setAttribute(name, wert === true ? "" : wert);
  }
  for (const kind of kinder.flat()) {
    if (kind != null) knoten.append(kind);
  }
  return knoten;
}

/** Zeigt Text an; Platzhalter werden gelb markiert, damit sie nicht übersehen werden. */
function textKnoten(text) {
  if (!istPlatzhalter(text)) return document.createTextNode(text);
  return el("span", { klasse: "platzhalter", text });
}

function dateiname() {
  const teil = location.pathname.split("/").pop();
  return teil === "" ? "index.html" : teil;
}

function baueKopf(daten) {
  const aktuell = dateiname();
  const gehoertZu = (ziel) => ziel === aktuell || (ziel === "galerien.html" && aktuell === "galerie.html");
  const liste = el(
    "ul",
    {},
    daten.navigation.map((punkt) =>
      el("li", {}, el("a", { href: punkt.ziel, text: punkt.text, "aria-current": gehoertZu(punkt.ziel) ? "page" : null })),
    ),
  );
  const menue = el("nav", { id: "hauptmenue", klasse: "hauptmenue", "aria-label": "Hauptmenü" }, liste);
  const knopf = el("button", { type: "button", klasse: "menue-knopf", "aria-expanded": "false", "aria-controls": "hauptmenue" });
  knopf.innerHTML =
    '<span class="nur-leser">Menü</span><svg aria-hidden="true" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>';
  const umschalten = (offen) => {
    menue.classList.toggle("offen", offen);
    knopf.setAttribute("aria-expanded", String(offen));
  };
  knopf.addEventListener("click", () => umschalten(!menue.classList.contains("offen")));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && menue.classList.contains("offen")) {
      umschalten(false);
      knopf.focus();
    }
  });
  return el(
    "header",
    { klasse: "kopf" },
    el("a", { klasse: "marke", href: "index.html", "aria-label": `${daten.name} – Startseite`, text: daten.name }),
    knopf,
    menue,
  );
}

function baueFuss(daten) {
  const links = el(
    "ul",
    {},
    daten.fusszeile.map((punkt) => el("li", {}, el("a", { href: punkt.ziel, text: punkt.text }))),
  );
  return el(
    "footer",
    { klasse: "fuss" },
    el("p", { klasse: "fuss-name" }, `© ${new Date().getFullYear()} ${daten.name}`, istPlatzhalter(daten.untertitel) ? null : ` · ${daten.untertitel}`),
    el("nav", { "aria-label": "Rechtliches" }, links),
  );
}

/** Füllt Felder aus inhalt/seiten.json (Name, E-Mail, Absätze, Schalter). */
async function fuelleSeitentexte() {
  const felder = document.querySelectorAll("[data-feld],[data-email],[data-absaetze],[data-wenn],[data-liste],[data-entwurf]");
  if (!felder.length) return;
  const seiten = await ladeJson("inhalt/seiten.json");
  const email = mailAdresse(seiten.inhaber);

  for (const knoten of document.querySelectorAll("[data-feld]")) {
    const wert = knoten.dataset.feld.split(".").reduce((o, k) => (o == null ? o : o[k]), seiten);
    if (typeof wert === "string") knoten.replaceChildren(textKnoten(wert));
  }
  for (const knoten of document.querySelectorAll("[data-absaetze]")) {
    const absaetze = seiten[knoten.dataset.absaetze] || [];
    knoten.replaceChildren(...absaetze.map((t) => el("p", {}, textKnoten(t))));
  }
  for (const knoten of document.querySelectorAll("[data-wenn]")) {
    knoten.hidden = !seiten[knoten.dataset.wenn];
  }
  for (const knoten of document.querySelectorAll("[data-email]")) {
    // Die Adresse steht nicht im HTML, sie wird erst hier aus zwei Teilen zusammengesetzt.
    if (!email) {
      if (knoten.dataset.email === "knopf") {
        knoten.removeAttribute("href");
        knoten.setAttribute("aria-disabled", "true");
      } else {
        knoten.replaceChildren(textKnoten("[HIER EINTRAGEN: E-Mail-Adresse]"));
        knoten.removeAttribute("href");
      }
      continue;
    }
    if (knoten.matches("a")) {
      knoten.href = `mailto:${email}`;
      if (knoten.dataset.email === "adresse") knoten.textContent = email;
    } else {
      knoten.textContent = email;
    }
  }
  for (const knoten of document.querySelectorAll("[data-liste]")) {
    const eintraege = seiten[knoten.dataset.liste] || [];
    knoten.replaceChildren(...eintraege.map((e) => el("li", {}, el("a", { href: e.ziel, text: e.text, rel: "noopener noreferrer" }))));
    knoten.hidden = eintraege.length === 0;
  }
  const offen = Object.values(seiten.inhaber).some(istPlatzhalter);
  for (const knoten of document.querySelectorAll("[data-entwurf]")) knoten.hidden = !offen;
}

function mailAdresse(inhaber) {
  const { email_lokal: lokal, email_domain: domain } = inhaber;
  if (!lokal || !domain || istPlatzhalter(lokal) || istPlatzhalter(domain)) return null;
  return `${lokal}@${domain}`;
}

async function start() {
  const daten = await seite;
  const seitenTitel = document.title;
  document.title = document.body.dataset.titelNurName === undefined ? `${seitenTitel} – ${daten.name}` : daten.name;
  const sprung = el("a", { klasse: "sprunglink", href: "#inhalt", text: "Zum Inhalt springen" });
  document.body.prepend(sprung, baueKopf(daten));
  document.body.append(baueFuss(daten));
  await fuelleSeitentexte();
  document.dispatchEvent(new CustomEvent("specktrum:bereit", { detail: daten }));
}

start().catch((fehler) => {
  console.error(fehler);
  const hinweis = el("p", { klasse: "fehler", role: "alert" }, "Die Seite konnte nicht geladen werden. Bitte über einen Webserver öffnen (siehe README) und die Seite neu laden.");
  document.body.prepend(hinweis);
});
