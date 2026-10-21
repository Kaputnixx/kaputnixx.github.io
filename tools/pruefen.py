#!/usr/bin/env python3
"""Prüft die Seite auf typische Fehler, bevor sie veröffentlicht wird.

    python tools/pruefen.py          (oder: bash tools/pruefen.sh, das auch die Tests startet)

FEHLER stoppen (Exit-Code 1), WARNUNGEN sind nur Hinweise:
  Fehler:   fehlende alt-Texte, doppelte IDs, kaputte lokale Links und Bildpfade,
            externe Adressen (außer in tools/externe-links-erlaubt.txt), Cookies/
            localStorage im Code, Metadaten (EXIF/GPS/XMP) in bilder/, Bilder aus
            fotos-quelle/ im Repo, Bilder der geschlossenen Galerie in bilder/.
  Warnung:  Bilder über 600 KB, Platzhalter "[HIER EINTRAGEN", Bilder mit Platzhalter-alt.
Braucht nur Python 3, kein Netz, keine weiteren Pakete.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metadaten import metadaten_in_datei  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent
GRENZE_BYTES = 600 * 1024
MARKER = "[HIER EINTRAGEN"
BILD_ENDUNGEN = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
URL = re.compile(r"https?://[^\s\"'`)<>\\]+", re.I)
CI = os.environ.get("GITHUB_ACTIONS") == "true"

fehler: list[str] = []
warnungen: list[str] = []


def melde(art: str, datei: Path | str, text: str) -> None:
    name = datei if isinstance(datei, str) else datei.relative_to(WURZEL).as_posix()
    (fehler if art == "FEHLER" else warnungen).append(f"{name}: {text}")
    if CI:
        print(f"::{'error' if art == 'FEHLER' else 'warning'} file={name}::{text}")


def lese(pfad: Path) -> str:
    return pfad.read_text(encoding="utf-8")


def erlaubte_links() -> list[str]:
    datei = WURZEL / "tools" / "externe-links-erlaubt.txt"
    if not datei.exists():
        return []
    zeilen = (z.strip() for z in lese(datei).splitlines())
    return [z for z in zeilen if z and not z.startswith("#")]


ERLAUBT = erlaubte_links()


def pruefe_extern(datei: Path, url: str) -> None:
    if not any(url.startswith(a) for a in ERLAUBT):
        melde("FEHLER", datei, f"externe Adresse {url} – nichts aus dem Netz einbinden. "
                               "Bewusst gesetzte Links in tools/externe-links-erlaubt.txt eintragen.")


def lokal_vorhanden(von: Path, ziel: str) -> bool:
    ziel = ziel.split("#", 1)[0].split("?", 1)[0]
    if not ziel:
        return True
    basis = WURZEL if ziel.startswith("/") else von.parent
    return (basis / ziel.lstrip("/")).resolve().exists()


class HtmlPruefer(HTMLParser):
    def __init__(self, datei: Path):
        super().__init__(convert_charrefs=True)
        self.datei = datei
        self.ids: dict[str, int] = {}
        self.anker: list[str] = []
        self.im_skript = False
        self.skripttext = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids[a["id"]] = self.ids.get(a["id"], 0) + 1
        if tag == "img" and "alt" not in a:
            melde("FEHLER", self.datei, f"<img> ohne alt-Attribut (Zeile {self.getpos()[0]})")
        if tag in ("script", "style"):
            self.im_skript = True
            self.skripttext = ""
        for name in ("href", "src", "poster", "action", "data"):
            wert = a.get(name)
            if wert:
                self._ziel(wert)
        for name in ("srcset",):
            for teil in (a.get(name) or "").split(","):
                if teil.strip():
                    self._ziel(teil.strip().split()[0])

    def _ziel(self, wert: str) -> None:
        if re.match(r"(https?:)?//", wert, re.I):
            pruefe_extern(self.datei, wert if wert.startswith("http") else "https:" + wert)
        elif re.match(r"(mailto|tel|data|javascript):", wert, re.I):
            return
        elif wert.startswith("#"):
            if len(wert) > 1:
                self.anker.append(wert[1:])
        elif not lokal_vorhanden(self.datei, wert):
            melde("FEHLER", self.datei, f"lokales Ziel '{wert}' existiert nicht (Zeile {self.getpos()[0]})")

    def handle_data(self, data):
        if self.im_skript:
            self.skripttext += data

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.im_skript:
            self.im_skript = False
            for url in URL.findall(self.skripttext):
                pruefe_extern(self.datei, url)


def pruefe_html() -> None:
    for datei in sorted(WURZEL.glob("*.html")):
        text = lese(datei)
        p = HtmlPruefer(datei)
        p.feed(text)
        for id_, n in p.ids.items():
            if n > 1:
                melde("FEHLER", datei, f"id '{id_}' kommt {n}-mal vor")
        # Sprungmarken auf Elemente, die erst per JavaScript entstehen, sind erlaubt
        for anker in p.anker:
            if anker not in p.ids:
                melde("FEHLER", datei, f"Sprungmarke #{anker} zeigt auf nichts")
        if MARKER in text:
            melde("WARNUNG", datei, f"{text.count(MARKER)} Platzhalter '{MARKER}' im Text")


JS_ZIEL = re.compile(r"""(["'`])((?:\./|\.\./)?[\w./-]+\.(?:html|json|js|css|svg))(?:[?#][^"'`]*)?\1""")


def pruefe_js_css() -> None:
    for datei in sorted((WURZEL / "js").glob("*.js")) + sorted((WURZEL / "css").glob("*.css")):
        text = lese(datei)
        for url in URL.findall(text):
            pruefe_extern(datei, url)
        if datei.suffix == ".css" and re.search(r"@import|url\(\s*[\"']?//", text):
            melde("FEHLER", datei, "@import oder protokollrelative url() – nichts nachladen")
        if datei.suffix == ".js":
            if re.search(r"\b(localStorage|sessionStorage|indexedDB|document\.cookie)\b", text):
                melde("FEHLER", datei, "Zugriff auf Speicher/Cookies – die Seite soll ohne auskommen")
            for m in JS_ZIEL.finditer(text):
                ziel = m.group(2)
                basis = datei if ziel.startswith(".") else WURZEL / "index.html"
                if not lokal_vorhanden(basis, ziel):
                    melde("FEHLER", datei, f"Datei '{ziel}' wird geladen, existiert aber nicht")


def ohne_beispiele(wert):
    """Schlüssel mit 'beispiel' im Namen sind nur Anschauungsmaterial und werden nicht geprüft."""
    if isinstance(wert, dict):
        return {k: ohne_beispiele(v) for k, v in wert.items() if "beispiel" not in k}
    if isinstance(wert, list):
        return [ohne_beispiele(v) for v in wert]
    return wert


def lade_json(pfad: Path):
    try:
        return json.loads(lese(pfad))
    except (json.JSONDecodeError, FileNotFoundError) as e:
        melde("FEHLER", pfad, f"JSON nicht lesbar: {e}")
        return None


def pruefe_inhalt() -> None:
    ordner = WURZEL / "inhalt"
    daten: dict[str, dict] = {}
    for datei in sorted(ordner.glob("*.json")):
        text = lese(datei)
        j = lade_json(datei)
        if j is None:
            continue
        daten[datei.name] = j
        for url in URL.findall(json.dumps(ohne_beispiele(j), ensure_ascii=False)):
            pruefe_extern(datei, url)
        if MARKER in text:
            melde("WARNUNG", datei, f"{text.count(MARKER)} Platzhalter '{MARKER}' noch nicht ersetzt")

    inhaber = daten.get("seiten.json", {}).get("inhaber", {})
    offene = [k for k, v in inhaber.items() if MARKER in str(v)]
    if offene:
        for seite_datei in ("impressum.html", "datenschutz.html"):
            melde("WARNUNG", WURZEL / seite_datei, f"zeigt noch Platzhalter ({', '.join(offene)}) aus inhalt/seiten.json")

    seite = daten.get("seite.json", {})
    for punkt in seite.get("navigation", []) + seite.get("fusszeile", []):
        if not lokal_vorhanden(WURZEL / "index.html", punkt.get("ziel", "")):
            melde("FEHLER", ordner / "seite.json", f"Menüziel '{punkt.get('ziel')}' existiert nicht")
    if not isinstance(daten.get("seiten.json", {}).get("impressum_voll"), bool):
        melde("FEHLER", ordner / "seiten.json", "'impressum_voll' muss true oder false sein")

    galerien = daten.get("galerien.json", {}).get("galerien", [])
    bilder = daten.get("galerien-daten.json", {}).get("galerien", {})
    for g in galerien:
        gid = g.get("id", "?")
        if g.get("externer_link"):
            if gid in bilder or (WURZEL / "bilder" / gid).exists():
                melde("FEHLER", ordner / "galerien.json", f"Galerie '{gid}' ist extern/geschlossen, hat aber Bilder im Repo")
            if g.get("titelbild") and g["titelbild"] not in [b["id"] for b in bilder.get("titelbilder", {}).get("bilder", [])]:
                melde("FEHLER", ordner / "galerien.json", f"Titelbild '{g['titelbild']}' von '{gid}' fehlt in galerien-daten.json")
        elif gid not in bilder:
            melde("FEHLER", ordner / "galerien.json", f"Galerie '{gid}' hat keine Bilder – 'python tools/galerien_bauen.py' ausführen")
    for gid, g in bilder.items():
        for b in g.get("bilder", []):
            for art in ("jpeg", "webp"):
                for v in b.get(art, []):
                    if not (WURZEL / v["pfad"]).is_file():
                        melde("FEHLER", ordner / "galerien-daten.json", f"Bilddatei {v['pfad']} fehlt")
            if not b.get("alt", "").strip():
                melde("FEHLER", ordner / "galerien-daten.json", f"{gid}/{b['id']}: alt-Text fehlt")



def pruefe_bilder() -> None:
    ordner = WURZEL / "bilder"
    if not ordner.is_dir():
        return
    for datei in sorted(ordner.rglob("*")):
        if not datei.is_file() or datei.suffix.lower() not in BILD_ENDUNGEN:
            continue
        gefunden = metadaten_in_datei(datei)
        if gefunden:
            melde("FEHLER", datei, f"enthält Metadaten ({', '.join(gefunden)}) – mit tools/galerien_bauen.py neu erzeugen")
        groesse = datei.stat().st_size
        if groesse > GRENZE_BYTES:
            melde("WARNUNG", datei, f"{groesse // 1024} KB groß (Grenze {GRENZE_BYTES // 1024} KB)")


def pruefe_repo() -> None:
    try:
        tracked = subprocess.run(["git", "ls-files", "fotos-quelle"], cwd=WURZEL, capture_output=True, text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        tracked = []  # kein Git verfügbar: überspringen
    if tracked:
        melde("FEHLER", "fotos-quelle/", f"{len(tracked)} Originaldateien sind im Repo – nie einchecken (git rm -r --cached fotos-quelle)")
    gitignore = WURZEL / ".gitignore"
    if not gitignore.exists() or "fotos-quelle/" not in lese(gitignore):
        melde("FEHLER", ".gitignore", "'fotos-quelle/' fehlt")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for pruefung in (pruefe_html, pruefe_js_css, pruefe_inhalt, pruefe_bilder, pruefe_repo):
        pruefung()
    for w in warnungen:
        print(f"WARNUNG  {w}")
    for f in fehler:
        print(f"FEHLER   {f}")
    print(f"\n{len(fehler)} Fehler, {len(warnungen)} Warnungen.")
    if not fehler and warnungen:
        print("Die Warnungen sind Hinweise (z. B. offene Platzhalter) und stoppen nichts.")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
