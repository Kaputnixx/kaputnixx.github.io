#!/usr/bin/env python3
"""Erzeugt synthetische Platzhalterbilder und baut daraus die Galerien.

    python tools/platzhalter_erzeugen.py

Es entstehen abstrakte Farbverläufe (keine echten Fotos, keine Gesichter,
keine Texte) in fotos-quelle/<Galerie>/platzhalter-NN.jpg. Der Zufall ist
reproduzierbar: derselbe Aufruf erzeugt immer dieselben Bilder.

Ordner, in denen schon eigene Dateien liegen, werden nicht angefasst.
Zum Ersetzen: die Dateien platzhalter-*.jpg löschen, eigene Fotos
hineinlegen und tools/galerien_bauen.py ausführen.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import galerien_bauen  # noqa: E402

LANGE_KANTE = 2400
FORMATE = [(3, 2), (3, 2), (2, 3), (4, 3), (1, 1), (16, 9), (4, 5)]

# Name, Anzahl, Stil, Farbpalette (Name -> RGB-Farben)
GALERIEN = [
    ("Landschaft", 8, "baender", [("Blau", (38, 70, 120)), ("Orange", (230, 140, 70)), ("Rosa", (220, 120, 140)), ("Grün", (60, 110, 80)), ("Gelb", (240, 200, 110))]),
    ("Natur und Tiere", 8, "blasen", [("Grün", (50, 110, 60)), ("Braun", (120, 85, 50)), ("Gelb", (210, 190, 80)), ("Dunkelgrün", (25, 60, 45)), ("Rot", (170, 70, 50))]),
    ("Makro", 7, "blasen", [("Violett", (110, 60, 150)), ("Rosa", (230, 120, 170)), ("Türkis", (50, 170, 170)), ("Gelb", (240, 210, 90)), ("Weiß", (235, 235, 240))]),
    ("Menschen und Porträt", 6, "verlauf", [("Beige", (205, 170, 140)), ("Braun", (110, 75, 60)), ("Rosé", (225, 160, 150)), ("Grau", (90, 90, 100)), ("Sand", (225, 205, 170))]),
    ("Nacht und Licht", 9, "lichter", [("Dunkelblau", (10, 14, 40)), ("Violett", (60, 30, 100)), ("Gelb", (255, 210, 110)), ("Rot", (230, 70, 80)), ("Cyan", (80, 200, 240))]),
]
TITELBILD_TISCHTENNIS = ("tischtennis", [("Türkis", (20, 90, 100)), ("Weiß", (230, 235, 235)), ("Orange", (230, 120, 50))])


def mische(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def verlauf(rng: random.Random, klein: tuple[int, int], farben) -> Image.Image:
    """Weicher Mehrpunktverlauf: kleines Zufallsraster, glatt hochgerechnet."""
    raster = Image.new("RGB", (5, 4))
    for x in range(5):
        for y in range(4):
            basis = rng.choice(farben)
            raster.putpixel((x, y), mische(basis, rng.choice(farben), rng.random() * 0.5))
    return raster.resize(klein, Image.BICUBIC)


def erzeuge(rng: random.Random, stil: str, farben, groesse: tuple[int, int]) -> Image.Image:
    # Gearbeitet wird klein und weich, erst am Ende vergrößert (schnell, ohne Kanten).
    w, h = groesse
    kleiner = 4
    klein = (w // kleiner, h // kleiner)
    bild = verlauf(rng, klein, farben)
    zeichnung = bild.copy()  # Grundfarbe statt Schwarz, sonst entstehen dunkle Ränder
    maske = Image.new("L", klein, 0)
    md = ImageDraw.Draw(maske)
    zd = ImageDraw.Draw(zeichnung)
    if stil == "baender":
        for _ in range(rng.randint(3, 5)):
            y = rng.randint(klein[1] // 4, klein[1])
            hoehe = rng.randint(klein[1] // 8, klein[1] // 3)
            zd.rectangle([0, y, klein[0], y + hoehe], fill=rng.choice(farben))
            md.rectangle([0, y, klein[0], y + hoehe], fill=rng.randint(90, 200))
        weich = klein[1] // 14
    elif stil in ("blasen", "lichter"):
        anzahl = rng.randint(5, 9) if stil == "blasen" else rng.randint(12, 22)
        for _ in range(anzahl):
            r = rng.randint(klein[0] // 14, klein[0] // 4) if stil == "blasen" else rng.randint(klein[0] // 40, klein[0] // 14)
            cx, cy = rng.randint(0, klein[0]), rng.randint(0, klein[1])
            farbe = rng.choice(farben)
            zd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=farbe)
            md.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rng.randint(110, 230))
        weich = klein[0] // (28 if stil == "blasen" else 60)
    else:  # "verlauf": nur Farbflächen, keine Formen
        weich = 1
        md.rectangle([0, 0, 1, 1], fill=0)
    maske = maske.filter(ImageFilter.GaussianBlur(max(weich, 1)))
    zeichnung = zeichnung.filter(ImageFilter.GaussianBlur(max(weich, 1)))
    bild = Image.composite(zeichnung, bild, maske)
    if stil == "lichter":  # Nacht: insgesamt abdunkeln
        bild = Image.blend(bild, Image.new("RGB", klein, (4, 6, 18)), 0.45)
    return bild.resize((w, h), Image.BICUBIC)


def farbwoerter(farben) -> str:
    namen = [n for n, _ in farben[:3]]
    return ", ".join(namen[:-1]) + " und " + namen[-1] if len(namen) > 1 else namen[0]


def erzeuge_galerie(ordner: Path, anzahl: int, stil: str, farben, ausgabe=print) -> bool:
    ordner.mkdir(parents=True, exist_ok=True)
    fremd = [p for p in ordner.iterdir() if p.is_file() and not p.name.startswith("platzhalter-") and p.name not in ("alt.txt", "unterschriften.txt")]
    if fremd:
        ausgabe(f"  übersprungen: {ordner.name} enthält eigene Dateien (z. B. {fremd[0].name}).")
        return False
    alt, unter = [], []
    for i in range(1, anzahl + 1):
        rng = random.Random(f"{ordner.name}-{i}")
        verh = FORMATE[rng.randrange(len(FORMATE))]
        a, b = verh
        groesse = (LANGE_KANTE, round(LANGE_KANTE * b / a)) if a >= b else (round(LANGE_KANTE * a / b), LANGE_KANTE)
        palette = rng.sample(farben, k=min(3, len(farben)))
        bild = erzeuge(rng, stil, [f for _, f in palette], groesse)
        name = f"platzhalter-{i:02d}.jpg"
        bild.save(ordner / name, "JPEG", quality=88)
        alt.append(f"{name}: Abstrakter Farbverlauf in {farbwoerter(palette)} (Platzhalterbild)")
        unter.append(f"{name}: Platzhalterbild {i} – wird später durch ein eigenes Foto ersetzt")
    (ordner / "alt.txt").write_text("\n".join(alt) + "\n", encoding="utf-8", newline="\n")
    (ordner / "unterschriften.txt").write_text("\n".join(unter) + "\n", encoding="utf-8", newline="\n")
    return True


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Erzeugt abstrakte Platzhalterbilder und baut die Galerien.")
    parser.add_argument("--wurzel", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)
    wurzel = args.wurzel.resolve()
    quelle = wurzel / "fotos-quelle"
    print("Erzeuge Platzhalterbilder (abstrakte Verläufe) ...")
    for name, anzahl, stil, farben in GALERIEN:
        ok = erzeuge_galerie(quelle / name, anzahl, stil, farben)
        if ok:
            print(f"  {name}: {anzahl} Bilder")
    # Kachelbild für die externe Galerie "Tischtennis": ohne Personen, ohne Bezug zum geschlossenen Bereich
    titel_ordner = quelle / galerien_bauen.TITELBILDER
    titel_ordner.mkdir(parents=True, exist_ok=True)
    tname, tfarben = TITELBILD_TISCHTENNIS
    if not (titel_ordner / f"{tname}.jpg").exists():
        rng = random.Random(f"titel-{tname}")
        erzeuge(rng, "blasen", [f for _, f in tfarben], (2400, 1600)).save(titel_ordner / f"{tname}.jpg", "JPEG", quality=88)
        (titel_ordner / "alt.txt").write_text(
            f"{tname}.jpg: Abstrakter Farbverlauf in Türkis, Weiß und Orange (Symbolbild)\n", encoding="utf-8", newline="\n"
        )
    print("\nBaue Galerien ...")
    try:
        z = galerien_bauen.bauen(wurzel)
    except galerien_bauen.BauFehler as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return 1
    print(f"\nFertig: {z.galerien} Galerien, {z.bilder_gesamt} Bilder ({z.neu} neu, {z.unveraendert} unverändert), "
          f"{z.bytes_gesamt / 1024 / 1024:.1f} MB in bilder/.")
    for w in z.warnungen:
        print(f"Warnung: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
