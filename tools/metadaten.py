"""Findet Metadaten (EXIF, GPS, XMP, IPTC) in JPEG-, WebP- und PNG-Dateien.

Reiner Python-Code ohne Pillow, damit er auch in den Prüfungen läuft, die
nichts installieren müssen. Er liest die Dateistruktur selbst, statt sich auf
ein Bildprogramm zu verlassen.
"""

from __future__ import annotations

import struct
from pathlib import Path


def metadaten_in_datei(pfad: Path) -> list[str]:
    """Liefert eine Liste der gefundenen Metadaten-Arten (leer = sauber)."""
    daten = Path(pfad).read_bytes()
    endung = Path(pfad).suffix.lower()
    if daten[:2] == b"\xff\xd8":
        return _jpeg(daten)
    if daten[:4] == b"RIFF" and daten[8:12] == b"WEBP":
        return _webp(daten)
    if daten[:8] == b"\x89PNG\r\n\x1a\n":
        return _png(daten)
    return [f"unbekanntes Format ({endung})"]


def _jpeg(daten: bytes) -> list[str]:
    funde = []
    pos = 2
    while pos + 4 <= len(daten):
        if daten[pos] != 0xFF:
            break
        marker = daten[pos + 1]
        if marker == 0xFF:  # Füllbyte
            pos += 1
            continue
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        if marker == 0xDA:  # Beginn der Bilddaten: danach keine Kopfdaten mehr
            break
        laenge = struct.unpack(">H", daten[pos + 2 : pos + 4])[0]
        inhalt = daten[pos + 4 : pos + 2 + laenge]
        if marker == 0xE1 and inhalt.startswith(b"Exif\x00\x00"):
            funde.append("EXIF")
        elif marker == 0xE1 and b"ns.adobe.com/xap" in inhalt[:40]:
            funde.append("XMP")
        elif marker == 0xED:
            funde.append("IPTC/Photoshop")
        elif marker == 0xFE:
            funde.append("Kommentar")
        pos += 2 + laenge
    return funde


def _webp(daten: bytes) -> list[str]:
    funde = []
    pos = 12
    while pos + 8 <= len(daten):
        kennung = daten[pos : pos + 4]
        laenge = struct.unpack("<I", daten[pos + 4 : pos + 8])[0]
        if kennung == b"EXIF":
            funde.append("EXIF")
        elif kennung == b"XMP ":
            funde.append("XMP")
        pos += 8 + laenge + (laenge & 1)
    return funde


def _png(daten: bytes) -> list[str]:
    funde = []
    pos = 8
    while pos + 8 <= len(daten):
        laenge = struct.unpack(">I", daten[pos : pos + 4])[0]
        kennung = daten[pos + 4 : pos + 8]
        if kennung == b"eXIf":
            funde.append("EXIF")
        elif kennung in (b"tEXt", b"iTXt", b"zTXt"):
            funde.append("Text/XMP")
        pos += 12 + laenge
    return funde
