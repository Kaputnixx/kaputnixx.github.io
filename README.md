# Specktrumgrafie – Foto-Portfolio

Eine schnelle, dunkle Foto-Seite aus reinem HTML, CSS und JavaScript. Kein Framework, kein Build-Schritt, keine Cookies, nichts aus dem Netz. Veröffentlicht wird sie mit GitHub Pages. Nur ein kleines Python-Werkzeug macht aus deinen Fotos die Webbilder.

> **Wichtig:** Dieses Repo ist **öffentlich**. Alles, was du hier hineinlegst, kann jeder lesen – auch später noch in der Versionshistorie. Deine Originalfotos (`fotos-quelle/`) bleiben deshalb **immer** außerhalb von Git (dafür sorgt die `.gitignore`).

## Inhalt

1. [Wie die Seite aufgebaut ist](#wie-die-seite-aufgebaut-ist)
2. [Fotos aus Lightroom Classic exportieren](#fotos-aus-lightroom-classic-exportieren)
3. [Fotos einfügen und Seite bauen](#fotos-einfügen-und-seite-bauen)
4. [Vorschau auf dem eigenen Rechner](#vorschau-auf-dem-eigenen-rechner)
5. [Hochladen (veröffentlichen)](#hochladen-veröffentlichen)
6. [Galerien hinzufügen, umbenennen, entfernen](#galerien-hinzufügen-umbenennen-entfernen)
7. [Wo steht was? (Name, Texte, Menü)](#wo-steht-was-name-texte-menü)
8. [Geschlossene Galerie „Tischtennis“](#geschlossene-galerie-tischtennis)
9. [Platzhalterbilder ersetzen](#platzhalterbilder-ersetzen)
10. [Prüfungen](#prüfungen)
11. [Checkliste vor dem ersten Veröffentlichen](#checkliste-vor-dem-ersten-veröffentlichen)

## Wie die Seite aufgebaut ist

| Ordner / Datei | Was ist das? |
| --- | --- |
| `index.html`, `galerien.html`, `galerie.html`, `ueber-mich.html`, `kontakt.html`, `impressum.html`, `datenschutz.html`, `404.html` | die Seiten |
| `css/stil.css` | das Aussehen (Farben stehen als Variablen ganz oben) |
| `js/` | die kleinen Programme (Diashow, Galerien, Lightbox) |
| `inhalt/` | **alle Texte und Einstellungen** (siehe unten) |
| `bilder/` | die fertigen Webbilder (werden vom Werkzeug erzeugt, **mit** eingecheckt) |
| `fotos-quelle/` | deine Originale – **nur auf deinem Rechner**, nie im Repo |
| `tools/` | Werkzeuge: Bilder bauen, Prüfungen |
| `tests/` | Selbsttests der Werkzeuge |

## Fotos aus Lightroom Classic exportieren

Im Bibliotheksmodul die Fotos einer Galerie markieren, dann **Datei → Exportieren** und diese Einstellungen wählen:

| Bereich | Einstellung |
| --- | --- |
| Exportort | Ordner: `…/fotos-quelle/<Galerie>/` (siehe nächster Abschnitt) |
| Dateibenennung | z. B. `Eigener Name – Sequenz` oder `Dateiname`. Die Namen bestimmen die **Reihenfolge** (alphabetisch) und tauchen später in den Bild-Adressen auf – also keine Namen von Personen oder Orten, die nicht öffentlich sein sollen. Tipp: `01-…`, `02-…` für eine feste Reihenfolge. |
| Dateieinstellungen | Bildformat **JPEG**, Farbraum **sRGB**, Qualität **85** |
| Bildgröße | „In Rahmen einpassen“, **Breite & Höhe**, lange Kante **3000 Pixel**, Auflösung egal, „Nicht vergrößern“ ankreuzen |
| Metadaten | **Nur Urheberrechtsvermerk** (Copyright). **Standortinformationen entfernen** ankreuzen. |
| Nachbearbeitung | Nichts weiter nötig |

Das Werkzeug entfernt beim Bauen **zusätzlich alle Metadaten** (EXIF, GPS-Standort, XMP, IPTC) aus jedem Bild. Der Export oben ist die erste Sicherung, das Werkzeug die zweite.

## Fotos einfügen und Seite bauen

Einmalig brauchst du Python 3 und das Paket Pillow:

```
python -m pip install pillow
```

1. Lege für jede Galerie einen Ordner in `fotos-quelle/` an und exportiere die Fotos dorthin:

   ```
   fotos-quelle/
     Landschaft/
       01-nebel.jpg
       02-see.jpg
       alt.txt            ← optional, Bildbeschreibungen
       unterschriften.txt ← optional, Bildunterschriften
     Makro/
       …
   ```

2. Optional: Beschreibungen für Screenreader und Suchmaschinen („alt-Texte“). In `alt.txt` pro Zeile `Dateiname: Beschreibung`:

   ```
   01-nebel.jpg: Morgennebel über einem See, im Hintergrund dunkle Tannen
   02-see.jpg: Ein Steg ragt in einen ruhigen Bergsee
   ```

   Ohne Eintrag steht dort „… (Beschreibung folgt)“. Mach die Beschreibungen kurz und sachlich. In `unterschriften.txt` (gleiches Format) stehen Bildunterschriften, die in der Großansicht erscheinen.

3. Bilder bauen (im Hauptordner des Repos):

   ```
   python tools/galerien_bauen.py
   ```

   Das Werkzeug erzeugt pro Foto drei Größen (640, 1280, 2200 Pixel) als JPEG und WebP unter `bilder/<galerie>/`, schreibt `inhalt/galerien-daten.json` und gibt am Ende eine Zusammenfassung aus (auch Warnungen, etwa bei Bildern über 600 KB). Es rechnet nur neue oder geänderte Bilder neu – ein weiterer Lauf dauert dann Sekunden.

   Bei Fehlern (z. B. ein defektes Bild) nennt es die Datei und was zu tun ist.

## Vorschau auf dem eigenen Rechner

Die Seite lädt ihre Texte aus Dateien. Ein Doppelklick auf `index.html` reicht darum **nicht**; starte einen kleinen Webserver:

```
python -m http.server 8000
```

Dann im Browser <http://localhost:8000> öffnen. Beenden mit `Strg + C`.

## Hochladen (veröffentlichen)

```
git add bilder inhalt
git commit -m "Neue Fotos in Landschaft"
git push
```

Gehst du über einen Pull Request, wird er automatisch geprüft (siehe [Prüfungen](#prüfungen)). Sobald der Stand auf `main` ist, veröffentlicht GitHub Pages ihn automatisch nach einer knappen Minute.

Einmalig muss in GitHub unter **Settings → Pages → Source** der Wert **„GitHub Actions“** eingestellt sein (oder per Kommandozeile `gh api -X PUT repos/<Nutzer>/<Repo>/pages -f build_type=workflow`).

## Galerien hinzufügen, umbenennen, entfernen

Die Reihenfolge und Namen der Galerien stehen in `inhalt/galerien.json`. Jeder Eintrag hat:

```json
{
  "id": "landschaft",
  "titel": "Landschaft",
  "beschreibung": "Weite, Licht und Stimmung.",
  "startseite": true
}
```

- `id`: Name des Ordners, kleingeschrieben, ohne Umlaute und Leerzeichen (`Menschen und Porträt` → `menschen-und-portraet`). Er steht in der Adresse (`galerie.html?name=landschaft`).
- `titel`, `beschreibung`: so wird sie angezeigt.
- `startseite`: `true` = ihre Bilder laufen in der Diashow auf der Startseite.

**Hinzufügen:** Ordner in `fotos-quelle/` anlegen, Fotos hinein, `python tools/galerien_bauen.py` ausführen. Der neue Eintrag wird am Ende von `galerien.json` ergänzt. Dort kannst du Titel, Beschreibung und die Reihenfolge anpassen (Einträge einfach verschieben).

**Umbenennen:** Nur `titel` in `galerien.json` ändern. Wenn auch die Adresse (`id`) neu sein soll: zuerst die `id` in `galerien.json` ändern, den Ordner in `fotos-quelle/` passend umbenennen und dann `python tools/galerien_bauen.py --aufraeumen` ausführen.

**Entfernen:** Ordner aus `fotos-quelle/` löschen, den Eintrag aus `galerien.json` löschen, dann

```
python tools/galerien_bauen.py --aufraeumen
```

(`--aufraeumen` löscht auch die zugehörigen Dateien in `bilder/`. Ohne diesen Schalter bleiben Galerien unangetastet, deren Quellordner auf diesem Rechner fehlt – praktisch, wenn du nur einen Teil deiner Originale dabeihast.)

**Einzelnes Foto entfernen:** Datei aus dem Quellordner löschen und das Werkzeug erneut starten.

## Wo steht was? (Name, Texte, Menü)

| Was | Wo |
| --- | --- |
| Name „Specktrumgrafie“, Untertitel, Menüpunkte, Fußzeile, Diashow-Tempo | `inhalt/seite.json` |
| Galerien (Titel, Reihenfolge, Startseite, externer Link) | `inhalt/galerien.json` |
| Dein Name, E-Mail, Über-mich-Texte, Kontakt-Links, Impressum-Schalter | `inhalt/seiten.json` |
| Alle Bilddaten (wird erzeugt, nicht von Hand ändern) | `inhalt/galerien-daten.json` |
| Farben und Abstände | `css/stil.css`, ganz oben |

**Den Namen änderst du nur in `inhalt/seite.json`** (`"name"`). Die Texte im Impressum und in der Datenschutzerklärung stehen dagegen direkt in `impressum.html` und `datenschutz.html`.

**E-Mail:** In `seiten.json` stehen die zwei Hälften getrennt (`email_lokal` = Teil vor dem @, `email_domain` = Teil danach). Der Browser setzt sie erst beim Anzeigen zusammen; im Quelltext steht die Adresse nie am Stück (einfacher Schutz vor Adress-Sammlern).

**Impressum:** Standardmäßig steht dort nur dein Name, die E-Mail-Adresse und der Satz „Diese Seite ist ein privates, nicht kommerzielles Angebot.“ Verkaufst du später Bilder oder nimmst Geld ein, setze in `seiten.json` `"impressum_voll": true` und trage die Anschrift ein; sie erscheint dann zusätzlich. Das ist keine Rechtsberatung – lass die Texte im Zweifel prüfen.

## Geschlossene Galerie „Tischtennis“

Das Repo und die Seite sind öffentlich. Ein Passwort auf der Seite würde die Bilder **nicht** schützen: die Dateien lägen offen im Repo, für immer in der Historie. Fotos der Tischtennis-Kollegen gehören deshalb in einen **geschützten externen Ordner** (Google Drive oder Google Fotos, nur per Freigabe-Link für die Gruppe).

Auf der Seite gibt es dafür nur eine Kachel. So schaltest du sie frei:

1. In `inhalt/galerien.json` beim Eintrag `tischtennis` den Platzhalter bei `externer_link` durch den Freigabe-Link ersetzen.
2. Den Link (oder dessen Anfang) in `tools/externe-links-erlaubt.txt` eintragen, sonst schlägt die Prüfung fehl.

Bis dahin zeigt die Kachel „bald verfügbar“ und ist nicht anklickbar. Lege **nie** Bilder, Dateinamen oder Beschreibungen aus diesem Bereich im Repo ab; das Werkzeug verweigert sogar einen Ordner `fotos-quelle/Tischtennis/`.

## Platzhalterbilder ersetzen

Zum Ausprobieren liegen abstrakte Farbverläufe (keine Fotos) unter `bilder/`. Sie wurden mit `python tools/platzhalter_erzeugen.py` erzeugt. Ersetzen:

1. In jedem Ordner von `fotos-quelle/` die Dateien `platzhalter-*.jpg`, `alt.txt` und `unterschriften.txt` löschen (oder den ganzen Ordner leeren).
2. Eigene Fotos hineinlegen (siehe oben).
3. `python tools/galerien_bauen.py` ausführen. Die alten Platzhalterbilder derselben Galerie werden dabei automatisch aus `bilder/` entfernt.

Das Kachelbild der Tischtennis-Kachel liegt in `fotos-quelle/titelbilder/tischtennis.jpg` (ein abstrakter Verlauf ohne Personen). Willst du es ändern, nimm ein neutrales Bild ohne Personen.

## Prüfungen

```
bash tools/pruefen.sh
```

führt die Selbsttests und die Seitenprüfung aus; dasselbe passiert bei jedem Pull Request auf GitHub. Geprüft wird u. a.: fehlende `alt`-Texte, doppelte IDs, kaputte Links und Bildpfade, **keine** externen Adressen im Code, **keine** Metadaten (EXIF/GPS) in `bilder/`, keine übergroßen Bilder. Offene Platzhalter (`[HIER EINTRAGEN`) erscheinen als **Warnung**; sie stoppen nichts, bleiben aber sichtbar, bis du sie ersetzt hast.

## Checkliste vor dem ersten Veröffentlichen

- [ ] `inhalt/seiten.json`: Name, E-Mail (beide Hälften), Über-mich-Texte ausgefüllt
- [ ] `inhalt/seite.json`: Untertitel ausgefüllt
- [ ] Impressum und Datenschutzerklärung gelesen und für deinen Fall geprüft (Musterinhalt, keine Rechtsberatung); bei Verkauf von Bildern `"impressum_voll": true`
- [ ] Alle `[HIER EINTRAGEN …]`-Platzhalter ersetzt (`python tools/pruefen.py` zeigt, welche noch offen sind)
- [ ] Platzhalterbilder durch eigene Fotos ersetzt, `alt.txt` gepflegt
- [ ] Einverständnis aller erkennbaren Personen auf den Bildern liegt vor (der Satz dazu steht auf „Über mich“ und in der Datenschutzerklärung)
- [ ] Standortdaten geprüft: Lightroom-Export ohne Standort, `bash tools/pruefen.sh` meldet keine Metadaten in `bilder/`
- [ ] Keine Originale im Repo (`git status` zeigt nichts aus `fotos-quelle/`)
- [ ] Tischtennis-Link gesetzt und in `tools/externe-links-erlaubt.txt` eingetragen – oder die Kachel bleibt auf „bald verfügbar“
- [ ] GitHub: Settings → Pages → Source = „GitHub Actions“
- [ ] Seite nach dem Veröffentlichen einmal auf dem Handy und am Rechner durchgeklickt
