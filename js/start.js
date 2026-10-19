// Startseite: Vollbild-Diashow aus den Galerien mit "startseite": true.
// Bedienung: Pfeiltasten, Wischen, Knöpfe. Pausiert bei Mauszeiger, Fokus und
// in versteckten Tabs. Mit "weniger Bewegung" läuft nichts von selbst.

import { seite, ladeGalerien, el, bildElement } from "./gemeinsam.js";

const weniger = matchMedia("(prefers-reduced-motion: reduce)");

const ICONS = {
  zurueck: '<svg aria-hidden="true" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>',
  weiter: '<svg aria-hidden="true" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7"/></svg>',
  pause: '<svg aria-hidden="true" viewBox="0 0 24 24" width="22" height="22" fill="currentColor"><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/></svg>',
  los: '<svg aria-hidden="true" viewBox="0 0 24 24" width="22" height="22" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>',
};

/** Reihum aus allen Startseiten-Galerien Bilder nehmen, damit die Mischung abwechslungsreich bleibt. */
function sammleFolien(galerien, maximal) {
  const quellen = galerien.filter((g) => g.startseite && !g.externer_link && g.bilder.length);
  const folien = [];
  for (let runde = 0; folien.length < maximal && quellen.some((g) => runde < g.bilder.length); runde++) {
    for (const g of quellen) {
      if (runde < g.bilder.length && folien.length < maximal) folien.push({ bild: g.bilder[runde], galerie: g });
    }
  }
  return folien;
}

function knopf(klasse, icon, beschriftung) {
  const k = el("button", { type: "button", klasse: `diashow-knopf ${klasse}`, "aria-label": beschriftung });
  k.innerHTML = icon;
  return k;
}

async function start() {
  const [daten, galerien] = await Promise.all([seite, ladeGalerien()]);
  const einstellungen = daten.diashow;
  const wurzel = document.getElementById("diashow");
  const folien = sammleFolien(galerien, einstellungen.max_bilder);

  if (!folien.length) {
    wurzel.append(el("div", { klasse: "diashow-leer" }, el("p", { text: "Hier erscheinen bald Bilder." }), el("a", { klasse: "knopf", href: "galerien.html", text: "Zu den Galerien" })));
    return;
  }

  wurzel.style.setProperty("--ueberblendung", `${einstellungen.ueberblendung_ms}ms`);
  wurzel.style.setProperty("--folien-dauer", `${einstellungen.dauer_ms + einstellungen.ueberblendung_ms}ms`);
  wurzel.classList.toggle("mit-zoom", Boolean(einstellungen.zoom));
  wurzel.setAttribute("aria-roledescription", "Diashow");

  const buehne = el("div", { klasse: "buehne" });
  const titel = el("a", { klasse: "folien-titel", href: "galerien.html" });
  const zaehler = el("span", { klasse: "zaehler", "aria-hidden": "true" });
  const zurueck = knopf("k-zurueck", ICONS.zurueck, "Vorheriges Bild");
  const weiter = knopf("k-weiter", ICONS.weiter, "Nächstes Bild");
  const pause = knopf("k-pause", ICONS.pause, "Diashow anhalten");
  const unten = el(
    "div",
    { klasse: "diashow-unten" },
    titel,
    el("div", { klasse: "steuerung" }, zaehler, zurueck, pause, weiter),
  );
  wurzel.append(buehne, unten);

  const knoten = new Array(folien.length).fill(null);
  let aktuell = -1;
  let timer = null;
  let nutzerPause = false;
  let ueberMaus = false;
  let imFokus = false;

  function folie(i) {
    if (knoten[i]) return knoten[i];
    const { bild, galerie } = folien[i];
    const k = el(
      "div",
      { klasse: "folie", role: "group", "aria-roledescription": "Bild", "aria-label": `${i + 1} von ${folien.length}`, "aria-hidden": "true" },
      bildElement(bild, { sizes: "100vw", eifrig: true, wichtig: i === 0, alt: `${bild.alt} (Galerie ${galerie.titel})` }),
    );
    knoten[i] = k;
    buehne.append(k);
    passeAn(i);
    return k;
  }

  /** Querformat füllt den Bildschirm, stark abweichende Formate werden ganz gezeigt statt beschnitten. */
  function passeAn(i) {
    const k = knoten[i];
    if (!k) return;
    const b = folien[i].bild;
    const abstand = Math.abs(Math.log(b.breite / b.hoehe / (buehne.clientWidth / Math.max(buehne.clientHeight, 1))));
    k.classList.toggle("passend", abstand > 0.5);
  }

  function geladen(k) {
    const bild = k.querySelector("img");
    if (bild.complete) return Promise.resolve();
    return new Promise((fertig) => {
      bild.addEventListener("load", fertig, { once: true });
      bild.addEventListener("error", fertig, { once: true });
      setTimeout(fertig, 4000); // nicht ewig auf ein langsames Bild warten
    });
  }

  async function zeige(index) {
    const neu = (index + folien.length) % folien.length;
    if (neu === aktuell) return;
    const k = folie(neu);
    await geladen(k);
    const alt = aktuell >= 0 ? knoten[aktuell] : null;
    for (const andere of knoten) andere?.classList.remove("vorher");
    if (alt) {
      alt.classList.remove("aktiv");
      alt.classList.add("vorher");
      alt.setAttribute("aria-hidden", "true");
      setTimeout(() => alt.classList.remove("vorher"), weniger.matches ? 0 : einstellungen.ueberblendung_ms + 100);
    }
    k.classList.add("aktiv");
    k.setAttribute("aria-hidden", "false");
    aktuell = neu;
    const { galerie } = folien[neu];
    titel.textContent = `${galerie.titel} →`;
    titel.href = `galerie.html?name=${encodeURIComponent(galerie.id)}`;
    zaehler.textContent = `${neu + 1} / ${folien.length}`;
    if (folien.length > 1) folie((neu + 1) % folien.length); // nächstes Bild schon mal laden
    planen();
  }

  const laeuft = () => !nutzerPause && !ueberMaus && !imFokus && !document.hidden && !weniger.matches && folien.length > 1;

  function planen() {
    clearTimeout(timer);
    wurzel.classList.toggle("pausiert", !laeuft());
    buehne.setAttribute("aria-live", laeuft() ? "off" : "polite");
    if (laeuft()) timer = setTimeout(() => zeige(aktuell + 1), einstellungen.dauer_ms);
  }

  function setzePause(an) {
    nutzerPause = an;
    pause.innerHTML = an ? ICONS.los : ICONS.pause;
    pause.setAttribute("aria-label", an ? "Diashow fortsetzen" : "Diashow anhalten");
    planen();
  }

  zurueck.addEventListener("click", () => zeige(aktuell - 1));
  weiter.addEventListener("click", () => zeige(aktuell + 1));
  pause.addEventListener("click", () => setzePause(!nutzerPause));
  pause.hidden = weniger.matches || folien.length < 2;
  zurueck.hidden = weiter.hidden = zaehler.hidden = folien.length < 2;

  document.addEventListener("keydown", (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.key === "ArrowLeft") zeige(aktuell - 1);
    else if (e.key === "ArrowRight") zeige(aktuell + 1);
  });

  wurzel.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") { ueberMaus = true; planen(); } });
  wurzel.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") { ueberMaus = false; planen(); } });
  unten.addEventListener("focusin", () => { imFokus = true; planen(); });
  unten.addEventListener("focusout", () => { imFokus = false; planen(); });
  document.addEventListener("visibilitychange", planen);
  weniger.addEventListener("change", () => { pause.hidden = weniger.matches || folien.length < 2; planen(); });
  addEventListener("resize", () => knoten.forEach((_, i) => passeAn(i)));

  // Wischen: waagerechte Bewegung über 50 px wechselt das Bild
  let start = null;
  wurzel.addEventListener("pointerdown", (e) => { start = { x: e.clientX, y: e.clientY }; });
  wurzel.addEventListener("pointerup", (e) => {
    if (!start) return;
    const dx = e.clientX - start.x;
    const dy = e.clientY - start.y;
    start = null;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) zeige(aktuell + (dx < 0 ? 1 : -1));
  });
  wurzel.addEventListener("pointercancel", () => { start = null; });

  await zeige(0);
}

document.addEventListener("specktrum:bereit", () => start().catch(console.error), { once: true });
