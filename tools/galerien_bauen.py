#!/usr/bin/env python3
"""Baut aus den Originalfotos die Webbilder für die Seite.

Aufruf (im Hauptordner des Repos):

    python tools/galerien_bauen.py

Was passiert:
  * Für jeden Unterordner von fotos-quelle/ entsteht eine Galerie.
  * Jedes Bild wird in drei Größen (lange Kante 640, 1280, 2200 px) als
    JPEG und WebP nach bilder/<galerie>/ geschrieben.
  * ALLE Metadaten (EXIF, GPS-Standort, XMP, IPTC) werden entfernt. Die
    Ausrichtung wird vorher angewendet, damit nichts auf dem Kopf steht.
  * inhalt/galerien-daten.json beschreibt alle Bilder für die Webseite.
  * Nur neue oder geänderte Bilder werden neu berechnet.

Benötigt Python 3 und Pillow (pip install pillow). Kein Netz nötig.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageOps

try:
    from PIL import ImageCms
except ImportError:  # pragma: no cover - ohne LittleCMS einfach ohne Profilumrechnung
    ImageCms = None

GROESSEN = (640, 1280, 2200)  # lange Kante in Pixeln
JPEG_QUALITAET = 82
WEBP_QUALITAET = 80
WARNGRENZE_BYTES = 600 * 1024  # Warnung für die größte Stufe
ENDUNGEN = {".jpg", ".jpeg", ".png"}
TITELBILDER = "titelbilder"  # Sonderordner für Kachelbilder ohne eigene Galerie
EINSTELLUNGEN = {
    "groessen": list(GROESSEN),
    "jpeg": JPEG_QUALITAET,
    "webp": WEBP_QUALITAET,
    "version": 1,
}


class BauFehler(Exception):
    """Fehler, der dem Nutzer verständlich erklärt werden kann."""


@dataclass
class Zusammenfassung:
    galerien: int = 0
    neu: int = 0
    unveraendert: int = 0
    bytes_gesamt: int = 0
    warnungen: list[str] = field(default_factory=list)
    bilder_gesamt: int = 0


def slug(text: str) -> str:
    """'Menschen und Porträt' -> 'menschen-und-portraet' (nur a-z, 0-9, Bindestrich)."""
    ersatz = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
    t = text.strip().lower()
    for alt, neu in ersatz.items():
        t = t.replace(alt, neu)
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t


def lese_json(pfad: Path, vorgabe: dict) -> dict:
    if not pfad.exists():
        return vorgabe
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise BauFehler(
            f"{pfad.name} ist kein gültiges JSON (Zeile {e.lineno}, Spalte {e.colno}: {e.msg}). "
            "Meist fehlt ein Komma oder ein Anführungszeichen."
        ) from e
    if not isinstance(daten, dict):
        raise BauFehler(f"{pfad.name}: Es wird ein JSON-Objekt {{ ... }} erwartet.")
    return daten


def schreibe_json(pfad: Path, daten: dict) -> bool:
    """Schreibt nur, wenn sich etwas ändert (saubere Git-Diffs). True = geschrieben."""
    text = json.dumps(daten, ensure_ascii=False, indent=2) + "\n"
    if pfad.exists() and pfad.read_text(encoding="utf-8") == text:
        return False
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with open(pfad, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return True


def lese_textzuordnung(pfad: Path) -> dict[str, str]:
    """Liest Zeilen der Form 'Dateiname: Text' (alt.txt, unterschriften.txt)."""
    if not pfad.exists():
        return {}
    ergebnis: dict[str, str] = {}
    for nr, zeile in enumerate(pfad.read_text(encoding="utf-8-sig").splitlines(), 1):
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#"):
            continue
        if ":" not in zeile:
            raise BauFehler(
                f"{pfad.parent.name}/{pfad.name}, Zeile {nr}: erwartet 'Dateiname: Beschreibung', gefunden: {zeile!r}"
            )
        name, text = zeile.split(":", 1)
        ergebnis[name.strip().lower()] = text.strip()
    return ergebnis


def finde_text(zuordnung: dict[str, str], datei: Path) -> str | None:
    return zuordnung.get(datei.name.lower()) or zuordnung.get(datei.stem.lower())


def quellbilder(ordner: Path) -> list[Path]:
    dateien = [
        p
        for p in ordner.iterdir()
        if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in ENDUNGEN
    ]
    dateien.sort(key=lambda p: (p.name.casefold(), p.name))
    gesehen: dict[str, Path] = {}
    for p in dateien:
        s = slug(p.stem)
        if not s:
            raise BauFehler(
                f"{ordner.name}/{p.name}: Der Dateiname enthält keine Buchstaben oder Ziffern. Bitte umbenennen."
            )
        if s in gesehen:
            raise BauFehler(
                f"{ordner.name}: '{gesehen[s].name}' und '{p.name}' ergeben denselben Ausgabenamen '{s}'. "
                "Bitte eine der Dateien umbenennen."
            )
        gesehen[s] = p
    return dateien


def pruefsumme(pfad: Path) -> str:
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def lade_bild(pfad: Path) -> Image.Image:
    """Öffnet ein Foto, dreht es richtig, rechnet nach sRGB und liefert ein
    Bild OHNE jegliche Metadaten (frisch aus den Pixeldaten aufgebaut)."""
    try:
        with Image.open(pfad) as roh:
            roh.load()
            bild = ImageOps.exif_transpose(roh)
            icc = roh.info.get("icc_profile")
            hat_alpha = bild.mode in ("RGBA", "LA", "PA") or "transparency" in bild.info
            if hat_alpha:
                rgba = bild.convert("RGBA")
                grund = Image.new("RGB", rgba.size, (0, 0, 0))
                grund.paste(rgba, mask=rgba.getchannel("A"))
                bild = grund
            elif bild.mode != "RGB":
                bild = bild.convert("RGB")
            if icc and not hat_alpha:
                bild = _nach_srgb(bild, icc)
            sauber = Image.frombytes("RGB", bild.size, bild.tobytes())
    except BauFehler:
        raise
    except Exception as e:  # Pillow wirft je nach Defekt verschiedene Fehler
        raise BauFehler(
            f"{pfad.parent.name}/{pfad.name}: Die Datei lässt sich nicht als Bild lesen "
            f"({type(e).__name__}: {e}). Bitte das Foto neu aus Lightroom exportieren."
        ) from e
    return sauber


def _nach_srgb(bild: Image.Image, icc: bytes) -> Image.Image:
    if ImageCms is None:
        return bild
    try:
        quelle = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        if "srgb" in ImageCms.getProfileDescription(quelle).lower():
            return bild
        return ImageCms.profileToProfile(bild, quelle, ImageCms.createProfile("sRGB"), outputMode="RGB")
    except Exception:
        return bild  # lieber unverändert als abbrechen


def stufen(lange_kante: int) -> list[int]:
    """Nie hochskalieren: nur Stufen unterhalb des Originals, dazu das Original selbst."""
    kleiner = [s for s in GROESSEN if s < lange_kante]
    if len(kleiner) < len(GROESSEN):
        kleiner.append(min(lange_kante, GROESSEN[-1]))
    return kleiner


def schreibe_bild(quelle: Path, wurzel: Path, rel_ziel: Path, name: str) -> dict:
    """Erzeugt alle Varianten eines Fotos in wurzel/rel_ziel; liefert die Beschreibung
    für die Daten (Pfade relativ zur Wurzel, mit Schrägstrichen)."""
    ziel = wurzel / rel_ziel
    bild = lade_bild(quelle)
    breite, hoehe = bild.size
    lange = max(breite, hoehe)
    ziel.mkdir(parents=True, exist_ok=True)
    varianten: dict[str, list[dict]] = {"jpeg": [], "webp": []}
    for stufe in stufen(lange):
        faktor = stufe / lange
        groesse = (max(1, round(breite * faktor)), max(1, round(hoehe * faktor)))
        klein = bild if groesse == bild.size else bild.resize(groesse, Image.LANCZOS)
        jpg = ziel / f"{name}-{stufe}.jpg"
        webp = ziel / f"{name}-{stufe}.webp"
        klein.save(jpg, "JPEG", quality=JPEG_QUALITAET, optimize=True, progressive=True)
        klein.save(webp, "WEBP", quality=WEBP_QUALITAET, method=4, exif=b"", xmp=b"")
        for art, datei in (("jpeg", jpg), ("webp", webp)):
            varianten[art].append(
                {"pfad": (rel_ziel / datei.name).as_posix(), "breite": groesse[0], "hoehe": groesse[1], "bytes": datei.stat().st_size}
            )
    gross = varianten["jpeg"][-1]
    return {"id": name, "breite": gross["breite"], "hoehe": gross["hoehe"], **varianten}


def bauen(wurzel: Path, aufraeumen: bool = False, ausgabe=print) -> Zusammenfassung:
    wurzel = Path(wurzel)
    quelle = wurzel / "fotos-quelle"
    bilder_ordner = wurzel / "bilder"
    inhalt = wurzel / "inhalt"
    if not quelle.is_dir():
        raise BauFehler(
            "Der Ordner 'fotos-quelle' fehlt. Lege dort pro Galerie einen Unterordner mit Fotos an "
            "(z. B. fotos-quelle/Landschaft/) oder erzeuge Platzhalter mit "
            "'python tools/platzhalter_erzeugen.py'."
        )

    galerien_datei = inhalt / "galerien.json"
    konfig = lese_json(galerien_datei, {"galerien": []})
    eintraege = konfig.setdefault("galerien", [])
    if not isinstance(eintraege, list) or not all(isinstance(e, dict) and "id" in e for e in eintraege):
        raise BauFehler("galerien.json: 'galerien' muss eine Liste von Einträgen mit 'id' sein.")
    bekannt = {e["id"]: e for e in eintraege}
    extern = {e["id"] for e in eintraege if e.get("externer_link")}

    ordner = sorted(
        (p for p in quelle.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))),
        key=lambda p: p.name.casefold(),
    )
    ids: dict[str, Path] = {}
    for p in ordner:
        s = slug(p.name)
        if not s:
            raise BauFehler(f"Der Ordnername '{p.name}' enthält keine Buchstaben oder Ziffern.")
        if s in ids:
            raise BauFehler(f"Die Ordner '{ids[s].name}' und '{p.name}' ergeben dieselbe Galerie '{s}'.")
        if s in extern:
            raise BauFehler(
                f"Der Ordner 'fotos-quelle/{p.name}' gehört zur externen, geschlossenen Galerie '{s}'. "
                "Deren Bilder dürfen nicht auf die öffentliche Seite. Bitte den Ordner aus "
                "fotos-quelle/ entfernen."
            )
        ids[s] = p

    zustand_datei = quelle / ".bauzustand.json"
    try:
        zustand = json.loads(zustand_datei.read_text(encoding="utf-8")) if zustand_datei.exists() else {}
    except json.JSONDecodeError:
        zustand = {}
    if zustand.get("einstellungen") != EINSTELLUNGEN:
        zustand = {"einstellungen": EINSTELLUNGEN, "bilder": {}}
    alt_zustand: dict = zustand["bilder"]
    neuer_zustand: dict = {}

    daten_datei = inhalt / "galerien-daten.json"
    vorher = lese_json(daten_datei, {"galerien": {}}).get("galerien", {})
    daten: dict[str, dict] = {} if aufraeumen else dict(vorher)

    z = Zusammenfassung()
    for gid, ordner_pfad in ids.items():
        dateien = quellbilder(ordner_pfad)
        if not dateien:
            z.warnungen.append(f"Ordner '{ordner_pfad.name}' enthält keine Bilder (jpg, jpeg, png) und wird übersprungen.")
            daten.pop(gid, None)
            continue
        alt_texte = lese_textzuordnung(ordner_pfad / "alt.txt")
        unterschriften = lese_textzuordnung(ordner_pfad / "unterschriften.txt")
        unbekannt = [n for n in {**alt_texte, **unterschriften} if not any(n in (d.name.lower(), d.stem.lower()) for d in dateien)]
        for n in unbekannt:
            z.warnungen.append(f"{ordner_pfad.name}: In alt.txt/unterschriften.txt steht '{n}', aber es gibt keine solche Datei.")

        titel = bekannt.get(gid, {}).get("titel") or ordner_pfad.name
        ziel = bilder_ordner / gid
        records = []
        behalten: set[str] = set()
        for nr, datei in enumerate(dateien, 1):
            name = slug(datei.stem)
            schluessel = f"{gid}/{name}"
            stat = datei.stat()
            alt_eintrag = alt_zustand.get(schluessel)
            record = None
            summe = None
            if alt_eintrag and all((wurzel / v["pfad"]).exists() for art in ("jpeg", "webp") for v in alt_eintrag["ausgabe"][art]):
                if alt_eintrag["groesse"] == stat.st_size and alt_eintrag["mtime_ns"] == stat.st_mtime_ns:
                    record, summe = alt_eintrag["ausgabe"], alt_eintrag["sha256"]
                else:
                    summe = pruefsumme(datei)
                    if summe == alt_eintrag["sha256"]:
                        record = alt_eintrag["ausgabe"]
            if record is None:
                ausgabe(f"  baue {gid}/{datei.name} ...")
                record = schreibe_bild(datei, wurzel, ziel.relative_to(wurzel), name)
                z.neu += 1
                summe = summe or pruefsumme(datei)
            else:
                z.unveraendert += 1
            neuer_zustand[schluessel] = {
                "groesse": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": summe,
                "ausgabe": record,
            }
            for art in ("jpeg", "webp"):
                for v in record[art]:
                    behalten.add(Path(v["pfad"]).name)
            for art in ("jpeg", "webp"):
                if record[art][-1]["bytes"] > WARNGRENZE_BYTES:
                    z.warnungen.append(
                        f"{record[art][-1]['pfad']} ist {record[art][-1]['bytes'] // 1024} KB groß "
                        f"(Grenze {WARNGRENZE_BYTES // 1024} KB). Qualität im Export senken oder Bild vereinfachen."
                    )
            records.append(
                {
                    "id": name,
                    "breite": record["breite"],
                    "hoehe": record["hoehe"],
                    "alt": finde_text(alt_texte, datei)
                    or f"Foto {nr} aus der Galerie {titel}",
                    "unterschrift": finde_text(unterschriften, datei) or "",
                    "jpeg": [{k: v[k] for k in ("pfad", "breite", "hoehe")} for v in record["jpeg"]],
                    "webp": [{k: v[k] for k in ("pfad", "breite", "hoehe")} for v in record["webp"]],
                }
            )
        # veraltete Dateien dieser Galerie entfernen (Bild gelöscht oder umbenannt)
        if ziel.is_dir():
            for f in ziel.iterdir():
                if f.is_file() and f.name not in behalten:
                    f.unlink()
        daten[gid] = {"titel": titel, "bilder": records}
        z.galerien += 1
        z.bilder_gesamt += len(records)

    # Übrig gebliebene Galerien (kein Quellordner auf diesem Rechner)
    fehlende = [g for g in daten if g not in ids]
    if aufraeumen:
        if bilder_ordner.is_dir():
            for p in bilder_ordner.iterdir():
                if p.is_dir() and p.name not in daten:
                    shutil.rmtree(p)
        # Zustand der nicht mehr vorhandenen Bilder verwerfen
    else:
        for g in fehlende:
            z.warnungen.append(
                f"Galerie '{g}' hat hier keinen Quellordner und bleibt unverändert. "
                "Mit --aufraeumen würde sie entfernt."
            )
    # Zustand der nicht bearbeiteten Galerien behalten (außer beim Aufräumen)
    if not aufraeumen:
        for k, v in alt_zustand.items():
            if k.split("/", 1)[0] not in ids:
                neuer_zustand.setdefault(k, v)

    # neue Ordner in galerien.json eintragen (am Ende, Reihenfolge ändert der Nutzer selbst)
    geaendert = False
    for gid, p in ids.items():
        if gid in bekannt or gid == TITELBILDER or gid not in daten:
            continue
        eintraege.append({"id": gid, "titel": p.name, "beschreibung": "", "startseite": False})
        z.warnungen.append(
            f"Neue Galerie '{p.name}' wurde am Ende von inhalt/galerien.json eingetragen "
            "(dort Titel, Beschreibung, Reihenfolge und 'startseite' anpassen)."
        )
        geaendert = True
    if geaendert:
        schreibe_json(galerien_datei, konfig)
    for e in eintraege:
        if e["id"] not in daten and not e.get("externer_link"):
            z.warnungen.append(f"Galerie '{e['id']}' steht in galerien.json, hat aber keine Bilder.")

    schreibe_json(daten_datei, {"galerien": daten})
    with open(zustand_datei, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"einstellungen": EINSTELLUNGEN, "bilder": neuer_zustand}, f, ensure_ascii=False, indent=1)
        f.write("\n")

    z.bytes_gesamt = sum(
        f.stat().st_size for f in bilder_ordner.rglob("*") if f.is_file()
    ) if bilder_ordner.is_dir() else 0
    return z


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Baut die Webbilder und inhalt/galerien-daten.json.")
    parser.add_argument("--wurzel", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="Hauptordner des Repos (Standard: Ordner über tools/)")
    parser.add_argument("--aufraeumen", action="store_true",
                        help="Galerien entfernen, zu denen es keinen Ordner in fotos-quelle/ gibt")
    args = parser.parse_args(argv)
    try:
        z = bauen(args.wurzel.resolve(), aufraeumen=args.aufraeumen)
    except BauFehler as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return 1
    print()
    print(f"Fertig: {z.galerien} Galerien, {z.bilder_gesamt} Bilder "
          f"({z.neu} neu berechnet, {z.unveraendert} unverändert).")
    print(f"Gesamtgröße von bilder/: {z.bytes_gesamt / 1024 / 1024:.1f} MB")
    for w in z.warnungen:
        print(f"Warnung: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
