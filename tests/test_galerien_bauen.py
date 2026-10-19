"""Selbsttest für tools/galerien_bauen.py.

Aufruf:  python -m unittest discover -s tests -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import galerien_bauen as gb  # noqa: E402
import metadaten  # noqa: E402


def foto_mit_metadaten(pfad: Path, groesse=(300, 200), ausrichtung=1):
    """Erzeugt ein JPEG mit EXIF (Kamera, Ausrichtung, GPS-Standort) und XMP."""
    bild = Image.new("RGB", groesse, (120, 80, 40))
    exif = Image.Exif()
    exif[0x010F] = "TestKamera"
    exif[0x0110] = "Modell X"
    exif[0x0112] = ausrichtung
    exif[0x8825] = {1: "N", 2: (52.0, 31.0, 12.0), 3: "E", 4: (13.0, 24.0, 36.0)}
    bild.save(pfad, "JPEG", exif=exif)
    return pfad


class BauTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.wurzel = Path(self._tmp.name)
        (self.wurzel / "inhalt").mkdir()
        (self.wurzel / "fotos-quelle" / "Test Galerie").mkdir(parents=True)
        self.quelle = self.wurzel / "fotos-quelle" / "Test Galerie"
        self.log = []

    def bauen(self, **kw):
        return gb.bauen(self.wurzel, ausgabe=self.log.append, **kw)

    def daten(self):
        return json.loads((self.wurzel / "inhalt" / "galerien-daten.json").read_text(encoding="utf-8"))

    # --- Datenschutz -------------------------------------------------------
    def test_metadaten_sind_weg(self):
        quelle = foto_mit_metadaten(self.quelle / "a.jpg")
        # Gegenprobe: Das Quellbild hat die Daten wirklich
        with Image.open(quelle) as original:
            self.assertIn(0x8825, original.getexif())
        self.assertIn(b"TestKamera", quelle.read_bytes())

        self.bauen()

        ausgaben = sorted((self.wurzel / "bilder" / "test-galerie").iterdir())
        self.assertEqual(len(ausgaben), 2)  # kleines Bild: eine Stufe, je JPEG und WebP
        for datei in ausgaben:
            with Image.open(datei) as bild:
                self.assertEqual(len(bild.getexif()), 0, f"{datei.name}: EXIF vorhanden")
                self.assertNotIn("exif", bild.info)
                self.assertNotIn("xmp", bild.info)
            rohdaten = datei.read_bytes()
            for spur in (b"TestKamera", b"Modell X", b"GPS", b"Exif", b"adobe"):
                self.assertNotIn(spur, rohdaten, f"{datei.name}: Spur {spur!r}")
            self.assertEqual(metadaten.metadaten_in_datei(datei), [], datei.name)

    def test_ausrichtung_wird_angewendet(self):
        foto_mit_metadaten(self.quelle / "hoch.jpg", groesse=(300, 200), ausrichtung=6)
        self.bauen()
        bild = self.daten()["galerien"]["test-galerie"]["bilder"][0]
        self.assertLess(bild["breite"], bild["hoehe"])  # 300x200 mit Drehung 6 -> hochkant

    # --- Größen ------------------------------------------------------------
    def test_groessen_und_formate(self):
        Image.new("RGB", (3000, 2000), (10, 20, 30)).save(self.quelle / "gross.jpg")
        self.bauen()
        bild = self.daten()["galerien"]["test-galerie"]["bilder"][0]
        self.assertEqual([v["breite"] for v in bild["jpeg"]], [640, 1280, 2200])
        self.assertEqual([v["breite"] for v in bild["webp"]], [640, 1280, 2200])
        for art in ("jpeg", "webp"):
            for v in bild[art]:
                self.assertTrue((self.wurzel / v["pfad"]).is_file(), v["pfad"])

    def test_kein_hochskalieren(self):
        Image.new("RGB", (900, 600), (10, 20, 30)).save(self.quelle / "klein.jpg")
        self.bauen()
        bild = self.daten()["galerien"]["test-galerie"]["bilder"][0]
        self.assertEqual([v["breite"] for v in bild["jpeg"]], [640, 900])

    # --- Reihenfolge, Texte ------------------------------------------------
    def test_reihenfolge_ist_stabil(self):
        for name in ("b.jpg", "C.jpg", "a.png", "10.jpg", "2.jpg"):
            Image.new("RGB", (100, 80), (1, 2, 3)).save(self.quelle / name)
        self.bauen()
        erste = (self.wurzel / "inhalt" / "galerien-daten.json").read_bytes()
        ids = [b["id"] for b in self.daten()["galerien"]["test-galerie"]["bilder"]]
        self.assertEqual(ids, ["10", "2", "a", "b", "c"])  # nach Dateiname sortiert
        self.bauen()
        self.assertEqual((self.wurzel / "inhalt" / "galerien-daten.json").read_bytes(), erste)

    def test_alt_texte_und_platzhalter(self):
        Image.new("RGB", (100, 80)).save(self.quelle / "eins.jpg")
        Image.new("RGB", (100, 80)).save(self.quelle / "zwei.jpg")
        (self.quelle / "alt.txt").write_text("# Kommentar\neins.jpg: Ein Baum im Nebel\n", encoding="utf-8-sig")
        (self.quelle / "unterschriften.txt").write_text("zwei: Zweites Bild\n", encoding="utf-8")
        self.bauen()
        eins, zwei = self.daten()["galerien"]["test-galerie"]["bilder"]
        self.assertEqual(eins["alt"], "Ein Baum im Nebel")
        self.assertIn("Beschreibung folgt", zwei["alt"])
        self.assertEqual(eins["unterschrift"], "")
        self.assertEqual(zwei["unterschrift"], "Zweites Bild")

    # --- Nur Geändertes neu bauen -----------------------------------------
    def test_nur_geaenderte_bilder_werden_neu_gebaut(self):
        Image.new("RGB", (100, 80), (1, 1, 1)).save(self.quelle / "a.jpg")
        Image.new("RGB", (100, 80), (2, 2, 2)).save(self.quelle / "b.jpg")
        z = self.bauen()
        self.assertEqual((z.neu, z.unveraendert), (2, 0))
        z = self.bauen()
        self.assertEqual((z.neu, z.unveraendert), (0, 2))
        Image.new("RGB", (100, 80), (9, 9, 9)).save(self.quelle / "b.jpg")
        z = self.bauen()
        self.assertEqual((z.neu, z.unveraendert), (1, 1))

    def test_geloeschtes_bild_verschwindet(self):
        Image.new("RGB", (100, 80)).save(self.quelle / "a.jpg")
        Image.new("RGB", (100, 80), (5, 5, 5)).save(self.quelle / "b.jpg")
        self.bauen()
        (self.quelle / "b.jpg").unlink()
        self.bauen()
        namen = {p.name for p in (self.wurzel / "bilder" / "test-galerie").iterdir()}
        self.assertTrue(all(n.startswith("a-") for n in namen), namen)

    # --- Fehlermeldungen ---------------------------------------------------
    def test_kaputtes_bild_gibt_verstaendliche_meldung(self):
        (self.quelle / "kaputt.jpg").write_bytes(b"das ist kein bild")
        with self.assertRaises(gb.BauFehler) as ctx:
            self.bauen()
        self.assertIn("kaputt.jpg", str(ctx.exception))
        self.assertIn("Lightroom", str(ctx.exception))

    def test_abgeschnittenes_bild(self):
        pfad = self.quelle / "halb.jpg"
        Image.effect_noise((400, 400), 60).convert("RGB").save(pfad, "JPEG")
        daten = pfad.read_bytes()
        pfad.write_bytes(daten[: len(daten) // 2])
        with self.assertRaises(gb.BauFehler) as ctx:
            self.bauen()
        self.assertIn("halb.jpg", str(ctx.exception))

    def test_fehlender_quellordner(self):
        (self.wurzel / "fotos-quelle" / "Test Galerie").rmdir()
        (self.wurzel / "fotos-quelle").rmdir()
        with self.assertRaises(gb.BauFehler) as ctx:
            self.bauen()
        self.assertIn("fotos-quelle", str(ctx.exception))

    def test_kaputtes_json(self):
        (self.wurzel / "inhalt" / "galerien.json").write_text('{"galerien": [ {"id": "x" "titel": 1} ]}', encoding="utf-8")
        with self.assertRaises(gb.BauFehler) as ctx:
            self.bauen()
        self.assertIn("galerien.json", str(ctx.exception))
        self.assertIn("Zeile", str(ctx.exception))

    def test_alt_txt_mit_falscher_zeile(self):
        Image.new("RGB", (100, 80)).save(self.quelle / "a.jpg")
        (self.quelle / "alt.txt").write_text("a.jpg Beschreibung ohne Doppelpunkt\n", encoding="utf-8")
        with self.assertRaises(gb.BauFehler) as ctx:
            self.bauen()
        self.assertIn("alt.txt", str(ctx.exception))

    def test_externe_galerie_darf_keine_bilder_haben(self):
        (self.wurzel / "inhalt" / "galerien.json").write_text(
            json.dumps({"galerien": [{"id": "test-galerie", "titel": "T", "externer_link": "https://beispiel.invalid/x"}]}),
            encoding="utf-8",
        )
        Image.new("RGB", (100, 80)).save(self.quelle / "a.jpg")
        with self.assertRaises(gb.BauFehler) as ctx:
            self.bauen()
        self.assertIn("extern", str(ctx.exception))
        self.assertFalse((self.wurzel / "bilder").exists())

    def test_neue_galerie_wird_in_galerien_json_eingetragen(self):
        Image.new("RGB", (100, 80)).save(self.quelle / "a.jpg")
        self.bauen()
        konfig = json.loads((self.wurzel / "inhalt" / "galerien.json").read_text(encoding="utf-8"))
        self.assertEqual([e["id"] for e in konfig["galerien"]], ["test-galerie"])
        self.assertEqual(konfig["galerien"][0]["titel"], "Test Galerie")

    def test_slug(self):
        self.assertEqual(gb.slug("Menschen und Porträt"), "menschen-und-portraet")
        self.assertEqual(gb.slug("  Nacht & Licht! "), "nacht-licht")
        self.assertEqual(gb.slug("Straße"), "strasse")


if __name__ == "__main__":
    unittest.main()
