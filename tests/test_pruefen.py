"""Prüft, dass tools/pruefen.py echte Probleme findet (und saubere Seiten durchlässt).

Aufruf:  python -m unittest discover -s tests -v
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

HAUPT = Path(__file__).resolve().parent.parent


class PruefenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.vorlage = Path(cls._tmp.name) / "vorlage"
        shutil.copytree(HAUPT, cls.vorlage, ignore=shutil.ignore_patterns(".git", "__pycache__", "fotos-quelle"))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def setUp(self):
        self.kopie = Path(tempfile.mkdtemp(dir=self._tmp.name))
        shutil.copytree(self.vorlage, self.kopie, dirs_exist_ok=True)

    def pruefe(self):
        r = subprocess.run([sys.executable, str(self.kopie / "tools" / "pruefen.py")], capture_output=True, text=True, encoding="utf-8")
        return r.returncode, r.stdout

    def test_saubere_seite_besteht_mit_warnungen(self):
        code, ausgabe = self.pruefe()
        self.assertEqual(code, 0, ausgabe)
        self.assertIn("WARNUNG", ausgabe)  # Platzhalter sind noch offen

    def aendere(self, datei, alt, neu):
        pfad = self.kopie / datei
        text = pfad.read_text(encoding="utf-8")
        self.assertIn(alt, text)
        pfad.write_text(text.replace(alt, neu, 1), encoding="utf-8")

    def test_bild_ohne_alt(self):
        self.aendere("kontakt.html", "<h1>Kontakt</h1>", '<h1>Kontakt</h1><img src="favicon.svg">')
        code, ausgabe = self.pruefe()
        self.assertEqual(code, 1)
        self.assertIn("ohne alt", ausgabe)

    def test_doppelte_id(self):
        self.aendere("kontakt.html", "<h1>Kontakt</h1>", '<h1 id="inhalt">Kontakt</h1>')
        code, ausgabe = self.pruefe()
        self.assertEqual(code, 1)
        self.assertIn("kommt 2-mal vor", ausgabe)

    def test_kaputter_link(self):
        self.aendere("kontakt.html", "<h1>Kontakt</h1>", '<h1>Kontakt</h1><a href="gibt-es-nicht.html">x</a>')
        code, ausgabe = self.pruefe()
        self.assertEqual(code, 1)
        self.assertIn("gibt-es-nicht.html", ausgabe)

    def test_externe_adresse(self):
        self.aendere("css/stil.css", "/* ---------- 1 Grundlagen", "@import url(https://fonts.example.invalid/x.css);\n/* ---------- 1 Grundlagen")
        code, ausgabe = self.pruefe()
        self.assertEqual(code, 1)
        self.assertIn("fonts.example.invalid", ausgabe)

    def test_externer_link_aus_erlaubnisliste(self):
        self.aendere("inhalt/galerien.json", "[HIER EINTRAGEN: Freigabe-Link]", "https://drive.example.invalid/ordner/abc")
        code, _ = self.pruefe()
        self.assertEqual(code, 1)  # nicht erlaubt
        with open(self.kopie / "tools" / "externe-links-erlaubt.txt", "a", encoding="utf-8") as f:
            f.write("https://drive.example.invalid/ordner/\n")
        code, ausgabe = self.pruefe()
        self.assertEqual(code, 0, ausgabe)

    def test_bild_mit_exif(self):
        ziel = next((self.kopie / "bilder" / "landschaft").glob("*-640.jpg"))
        exif = Image.Exif()
        exif[0x8825] = {1: "N", 2: (52.0, 31.0, 12.0), 3: "E", 4: (13.0, 24.0, 36.0)}
        Image.new("RGB", (64, 64)).save(ziel, "JPEG", exif=exif)
        code, ausgabe = self.pruefe()
        self.assertEqual(code, 1)
        self.assertIn("Metadaten", ausgabe)

    def test_geschlossene_galerie_darf_keine_bilder_haben(self):
        (self.kopie / "bilder" / "tischtennis").mkdir()
        code, ausgabe = self.pruefe()
        self.assertEqual(code, 1)
        self.assertIn("extern/geschlossen", ausgabe)

    def test_speicher_im_code(self):
        with open(self.kopie / "js" / "gemeinsam.js", "a", encoding="utf-8") as f:
            f.write('\nwindow.localStorage.setItem("x", "y");\n')
        code, ausgabe = self.pruefe()
        self.assertEqual(code, 1)
        self.assertIn("Speicher", ausgabe)

    def test_groesse_ist_nur_warnung(self):
        ziel = next((self.kopie / "bilder" / "landschaft").glob("*-640.jpg"))
        with open(ziel, "ab") as f:
            f.write(b"\0" * (700 * 1024))  # Anhang hinter dem Bildende
        code, ausgabe = self.pruefe()
        self.assertEqual(code, 0, ausgabe)
        self.assertIn("KB groß", ausgabe)


if __name__ == "__main__":
    unittest.main()
