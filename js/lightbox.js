// Lightbox: Vollbildansicht mit Pfeiltasten, Wischen, Escape, Bildnummer und Unterschrift.
// Nutzt das eingebaute <dialog>: Fokus-Falle und Escape kommen vom Browser.

import { el, bildElement } from "./gemeinsam.js";

const ICON = {
  zu: '<svg aria-hidden="true" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  zurueck: '<svg aria-hidden="true" viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>',
  weiter: '<svg aria-hidden="true" viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg>',
};

let dialog = null;
let zustand = { bilder: [], index: 0, ausloeser: null };
let teile = {};

function knopf(klasse, icon, beschriftung) {
  const k = el("button", { type: "button", klasse: `lb-knopf ${klasse}`, "aria-label": beschriftung });
  k.innerHTML = icon;
  return k;
}

function baue() {
  teile.buehne = el("div", { klasse: "lb-buehne" });
  teile.zaehler = el("span", { klasse: "lb-zaehler" });
  teile.text = el("p", { klasse: "lb-text" });
  teile.zu = knopf("lb-zu", ICON.zu, "Schließen");
  teile.zurueck = knopf("lb-zurueck", ICON.zurueck, "Vorheriges Bild");
  teile.weiter = knopf("lb-weiter", ICON.weiter, "Nächstes Bild");
  dialog = el(
    "dialog",
    { klasse: "lightbox", "aria-label": "Bildansicht" },
    teile.buehne,
    teile.zu,
    teile.zurueck,
    teile.weiter,
    el("div", { klasse: "lb-fuss" }, teile.zaehler, teile.text),
  );
  document.body.append(dialog);

  teile.zu.addEventListener("click", () => dialog.close());
  teile.zurueck.addEventListener("click", () => zeige(zustand.index - 1));
  teile.weiter.addEventListener("click", () => zeige(zustand.index + 1));
  teile.buehne.addEventListener("click", (e) => {
    if (!(e.target instanceof HTMLImageElement)) dialog.close(); // Klick neben das Bild schließt
  });
  dialog.addEventListener("keydown", (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.key === "ArrowLeft") zeige(zustand.index - 1);
    else if (e.key === "ArrowRight") zeige(zustand.index + 1);
  });
  dialog.addEventListener("close", () => {
    document.documentElement.classList.remove("lb-offen");
    zustand.ausloeser?.focus?.();
  });

  let start = null;
  dialog.addEventListener("pointerdown", (e) => { start = { x: e.clientX, y: e.clientY }; });
  dialog.addEventListener("pointerup", (e) => {
    if (!start) return;
    const dx = e.clientX - start.x;
    const dy = e.clientY - start.y;
    start = null;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) zeige(zustand.index + (dx < 0 ? 1 : -1));
  });
}

function vorladen(bild) {
  const i = new Image();
  i.sizes = "100vw";
  i.srcset = bild.jpeg.map((v) => `${v.pfad} ${v.breite}w`).join(", ");
  i.src = bild.jpeg[bild.jpeg.length - 1].pfad;
}

let nummerZaehler = 0;

function zeige(nummer) {
  const { bilder } = zustand;
  const index = (nummer + bilder.length) % bilder.length;
  zustand.index = index;
  const bild = bilder[index];
  // Das alte Bild bleibt stehen, bis das neue geladen ist (kein schwarzes Aufblitzen).
  const neu = bildElement(bild, { sizes: "100vw", eifrig: true });
  const ich = ++nummerZaehler;
  const einsetzen = () => { if (ich === nummerZaehler) teile.buehne.replaceChildren(neu); };
  const img = neu.querySelector("img");
  if (img.complete) einsetzen();
  else {
    img.addEventListener("load", einsetzen, { once: true });
    img.addEventListener("error", einsetzen, { once: true });
    if (!teile.buehne.firstChild) einsetzen(); // erstes Bild: sofort Rahmen zeigen
  }
  teile.zaehler.textContent = `${index + 1} / ${bilder.length}`;
  teile.text.textContent = bild.unterschrift || "";
  teile.text.hidden = !bild.unterschrift;
  if (bilder.length > 1) {
    vorladen(bilder[(index + 1) % bilder.length]);
    vorladen(bilder[(index - 1 + bilder.length) % bilder.length]);
  }
}

/** Öffnet die Lightbox. `ausloeser` bekommt beim Schließen den Fokus zurück. */
export function oeffneLightbox(bilder, index, ausloeser) {
  if (!dialog) baue();
  zustand = { bilder, index, ausloeser };
  const einzeln = bilder.length < 2;
  teile.zurueck.hidden = teile.weiter.hidden = einzeln;
  zeige(index);
  document.documentElement.classList.add("lb-offen");
  dialog.showModal();
}
