// Galerieübersicht: eine Kachel pro Galerie, dazu die externe, geschlossene Galerie.

import { ladeGalerien, el, bildElement, istPlatzhalter } from "./gemeinsam.js";

const SCHLOSS =
  '<svg aria-hidden="true" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="11" width="14" height="9" rx="1.5"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>';
const GROESSEN = "(min-width: 64rem) 33vw, (min-width: 40rem) 50vw, 100vw";

function titelbildVon(galerie) {
  if (galerie.titelbild) return galerie.titelbilder.find((b) => b.id === galerie.titelbild) ?? null;
  return galerie.bilder[0] ?? null;
}

function kachel(galerie, nr) {
  const cover = titelbildVon(galerie);
  const bild = el("span", { klasse: "kachel-bild" }, cover ? bildElement(cover, { sizes: GROESSEN, alt: "", eifrig: nr < 3 }) : null);
  const extern = Boolean(galerie.externer_link);
  const bereit = extern && !istPlatzhalter(galerie.externer_link);

  const zusatz = extern ? "geschlossener Bereich" : `${galerie.bilder.length} ${galerie.bilder.length === 1 ? "Bild" : "Bilder"}`;
  const titelZeile = el("span", { klasse: "kachel-titel" }, galerie.titel);
  if (extern) {
    const schloss = el("span", { klasse: "kachel-schloss" });
    schloss.innerHTML = SCHLOSS;
    titelZeile.prepend(schloss);
  }
  const text = el(
    "span",
    { klasse: "kachel-text" },
    titelZeile,
    " ", // Leerzeichen für Screenreader (sieht man nicht)
    el("span", { klasse: "kachel-zusatz" }, zusatz, extern && !bereit ? " · bald verfügbar" : ""),
  );

  if (!extern) {
    return el("li", { klasse: "kachel" }, el("a", { klasse: "kachel-link", href: `galerie.html?name=${encodeURIComponent(galerie.id)}` }, bild, text));
  }
  if (!bereit) {
    // Link noch nicht eingetragen: Kachel zeigen, aber nicht anklickbar
    return el("li", { klasse: "kachel gesperrt" }, el("div", { klasse: "kachel-link" }, bild, text));
  }
  return el(
    "li",
    { klasse: "kachel" },
    el(
      "a",
      { klasse: "kachel-link", href: galerie.externer_link, target: "_blank", rel: "noopener noreferrer" },
      bild,
      text,
      el("span", { klasse: "nur-leser" }, " (öffnet in neuem Tab)"),
    ),
  );
}

async function start() {
  const galerien = await ladeGalerien();
  const liste = document.getElementById("kacheln");
  liste.replaceChildren(...galerien.filter((g) => g.externer_link || g.bilder.length).map(kachel));
}

document.addEventListener("specktrum:bereit", () => start().catch(console.error), { once: true });
