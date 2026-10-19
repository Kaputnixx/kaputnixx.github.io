// Eine Galerie als ruhiges Raster (Zeilen gleicher Höhe) mit Lightbox.
// Aufruf: galerie.html?name=<id aus inhalt/galerien.json>

import { ladeGalerien, el, bildElement } from "./gemeinsam.js";
import { oeffneLightbox } from "./lightbox.js";

const GROESSEN = "(min-width: 48rem) 33vw, 60vw";

async function start(seitenDaten) {
  const name = new URLSearchParams(location.search).get("name");
  const galerien = await ladeGalerien();
  const galerie = galerien.find((g) => g.id === name && !g.externer_link && g.bilder.length);
  const titel = document.getElementById("titel");
  const beschreibung = document.getElementById("beschreibung");
  const raster = document.getElementById("raster");

  if (!galerie) {
    titel.textContent = "Galerie nicht gefunden";
    beschreibung.textContent = "Diese Galerie gibt es nicht. Hier geht es zur Übersicht:";
    raster.replaceWith(el("p", {}, el("a", { klasse: "knopf", href: "galerien.html", text: "Alle Galerien" })));
    return;
  }

  document.title = `${galerie.titel} – ${seitenDaten.name}`;
  titel.textContent = galerie.titel;
  beschreibung.textContent = galerie.beschreibung || "";
  beschreibung.hidden = !galerie.beschreibung;

  const links = galerie.bilder.map((bild, nr) => {
    const grosse = bild.jpeg[bild.jpeg.length - 1];
    const link = el(
      "a",
      { klasse: "raster-link", href: grosse.pfad },
      bildElement(bild, { sizes: GROESSEN, eifrig: nr < 3, wichtig: nr === 0 }),
    );
    link.addEventListener("click", (e) => {
      if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return; // Neuer Tab usw. bleibt möglich
      e.preventDefault();
      oeffneLightbox(galerie.bilder, nr, link);
    });
    const eintrag = el("li", { klasse: "raster-eintrag" }, link);
    eintrag.style.setProperty("--verh", (bild.breite / bild.hoehe).toFixed(4));
    return eintrag;
  });
  raster.replaceChildren(...links);
}

document.addEventListener("specktrum:bereit", (e) => start(e.detail).catch(console.error), { once: true });
