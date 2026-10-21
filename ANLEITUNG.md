# Anleitung: Seite ändern und wieder online stellen

Kurzfassung: **ändern → lokal ansehen → hochladen.** Nach dem Hochladen ist die Änderung nach etwa einer Minute online. Alle Befehle gibst du in PowerShell **im Ordner `portfolio`** ein.

> **Wichtig:** Dieses Repo ist **öffentlich**. Alles, was du hochlädst, kann jeder lesen, auch später noch in der Versionshistorie. Lege nie Originalfotos, Bilder mit Standortdaten oder private Texte hinein. Der Ordner `fotos-quelle/` wird durch die `.gitignore` nie hochgeladen.

## 1. Was ändere ich wo?

| Was du ändern willst | Datei oder Ordner |
| --- | --- |
| Über-mich-Texte, dein Name, E-Mail, Kontakt-Links | `inhalt/seiten.json` |
| Name der Seite, Untertitel, Menü, Fußzeile, Diashow-Tempo | `inhalt/seite.json` |
| Galerietitel, Beschreibung, Reihenfolge, Startseite | `inhalt/galerien.json` |
| Impressum, Datenschutzerklärung | direkt in `impressum.html` und `datenschutz.html` |
| Farben und Abstände | `css/stil.css`, ganz oben |
| **Neue Bilder hinzufügen** | JPEGs in `fotos-quelle/<Galerie>/` legen, dann Schritt 2 |
| **Bild entfernen** | Datei aus `fotos-quelle/<Galerie>/` löschen, dann Schritt 2 |

Die Textdateien (`.json`) öffnest du mit einem Editor und änderst nur den Text zwischen den Anführungszeichen. Lass Doppelpunkte, Kommas und Klammern stehen, sonst bricht die Seite. Die Datei `inhalt/galerien-daten.json` wird vom Werkzeug erzeugt und nie von Hand geändert.

## 2. Neue Bilder vorbereiten

Die Bilder müssen **JPEG** sein: Farbraum sRGB, lange Kante 3000 Pixel, Qualität etwa 85, **ohne Standortdaten**. Aus Lightroom Classic exportierst du so: *Datei → Exportieren*, Format JPEG, sRGB, Qualität 85, „In Rahmen einpassen“ mit 3000 Pixel lange Kante, „Nicht vergrößern“, Metadaten „Nur Urheberrechtsvermerk“, **Standortinformationen entfernen**.

Lege die Dateien in den Ordner der passenden Galerie in `fotos-quelle/` (`landschaft`, `makro`, `menschen-und-portraet`, `nacht-und-licht`, `natur-und-tiere`). Die Dateinamen bestimmen die Reihenfolge (alphabetisch), zum Beispiel `01.jpg`, `02.jpg`. Keine Namen von Personen oder Orten verwenden, die nicht öffentlich sein sollen. Wenn du neue Bilder in eine Galerie legst, die schon Bilder hat, nimm Nummern, die noch nicht vergeben sind.

Dann erzeugt das Werkzeug die Web-Bilder (drei Größen, JPEG und WebP) und entfernt alle Metadaten:

```
python tools/galerien_bauen.py
```

Es rechnet nur neue oder geänderte Bilder. Warnungen zur Dateigröße (über 600 KB) sind Hinweise und stoppen nichts.

Beschreibungen für Screenreader sind optional: In `fotos-quelle/<Galerie>/alt.txt` steht pro Zeile `Dateiname: Beschreibung`. Ohne Eintrag steht dort ein neutraler Text wie „Foto 3 aus der Galerie Landschaft“.

## 3. Lokal ansehen

```
python -m http.server 8000
```

Dann im Browser <http://localhost:8000> öffnen und die geänderte Stelle prüfen. Beenden mit `Strg + C`. Ein Doppelklick auf `index.html` reicht nicht, die Seite lädt ihre Texte aus Dateien.

## 4. Online stellen

```
python tools/pruefen.py
git add bilder inhalt tools css *.html
git commit -m "Kurz beschreiben, was du geändert hast"
git push
```

`python tools/pruefen.py` sollte am Ende `0 Fehler` melden (Warnungen sind erlaubt). Nach dem `git push` baut GitHub die Seite von selbst. Unter dem Reiter **Actions** im GitHub-Repo siehst du den Lauf. Ein grüner Haken heißt: online. Bei einem roten Kreuz bleibt die Seite wie sie war, und die Fehlermeldung steht im Lauf.

## 5. Eine Änderung zurücknehmen

Hast du etwas hochgeladen, das nicht bleiben soll:

```
git revert HEAD
git push
```

Das macht den letzten Stand rückgängig. Die Bilder bleiben in der Historie sichtbar. Bei Standortdaten oder Privatem in einem hochgeladenen Bild reicht das **nicht**; hol dir dann Hilfe, bevor du weitermachst.

## 6. Mehr Details

Alle Einstellungen, Galerien hinzufügen oder umbenennen, die Prüfungen und die Checkliste vor dem Veröffentlichen stehen in der `README.md`.
