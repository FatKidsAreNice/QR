# create_heatmap.py
"""
Analysesoftware zur Visualisierung von Bewegungsdaten (Heatmap).

Zweck
-----
Dieses Modul generiert eine grafische Auswertung der historischen Tracking-Daten:
1. Daten-Extraktion: Lädt alle gespeicherten Koordinaten aus der SQLite-Datenbank.
2. Aggregation: Addiert Bewegungen auf einer 2D-Maske (Accumulator-Prinzip).
   Häufig frequentierte Bereiche werden "heißer" (höhere Werte).
3. Visualisierung: Legt eine Falschfarben-Darstellung (Jet-Colormap) über den 
   Hallenplan, um Hotspots und Hauptverkehrswege (Trampelpfade) sichtbar zu machen.

Design-Notizen
--------------
- Datentyp Float32: Der Accumulator nutzt `float32` statt `uint8`. Das ist zwingend 
  nötig, da an stark frequentierten Stellen der Wert schnell über 255 steigen würde 
  (Overflow). Erst ganz am Ende wird auf 0-255 normalisiert.
- Overlay-Technik: Die Heatmap wird mittels `addWeighted` transparent über den 
  Grundriss gelegt, damit räumliche Bezüge (Regale, Wände) erkennbar bleiben.
"""

import cv2
import numpy as np
import os
import sys

# Eigene Module
from database import DatabaseManager
import config

def generate_heatmap():
    """
    Hauptfunktion zur Erstellung und Speicherung der Heatmap.
    """
    print("\n--- Generiere Heatmap aus DB-Daten ---\n")
    
    # ---------- 1. Ressourcen laden (Grundriss) ----------
    try:
        # Versuche Pfad aus Config
        map_img = cv2.imread(config.MAP_FILE)
    except:
        pass # Fallback wird unten geprüft

    if map_img is None:
        # Fallback: Suche im lokalen Verzeichnis
        map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grundriss.png")
        map_img = cv2.imread(map_path)
        
    if map_img is None:
        print("❌ FEHLER: Grundriss-Datei nicht gefunden. Abbruch.")
        return

    height, width = map_img.shape[:2]

    # ---------- 2. Daten-Akquise (Datenbank) ----------
    try:
        db = DatabaseManager()
        points = db.get_all_movements()
        print(f"[DATA] {len(points)} Datenpunkte aus der Historie geladen.")
    except Exception as e:
        print(f"❌ Datenbankfehler: {e}")
        return

    if not points:
        print("⚠️  Keine Daten vorhanden. Bitte das Tracking erst eine Weile laufen lassen!")
        return

    # ---------- 3. Initialisierung (Accumulator) ----------
    # Wir erstellen eine leere Matrix mit Float-Präzision, um Überläufe zu vermeiden.
    heatmap_mask = np.zeros((height, width), dtype=np.float32)

    print("[CALC] Berechne Dichte-Verteilung (das kann kurz dauern)...")

    # ---------- 4. Rendering (Punkt-Aggregation) ----------
    # Jeder Punkt erhöht die "Temperatur" an seiner Koordinate.
    for row in points:
        x, y = row['x'], row['y']
        
        # Boundary-Check: Liegt der Punkt im Bild?
        if 0 <= x < width and 0 <= y < height:
            # Wir erstellen einen temporären Layer mit einem "Klecks" (Kreis)
            # Radius = 25px, Intensität = 1.0
            temp_layer = np.zeros((height, width), dtype=np.float32)
            cv2.circle(temp_layer, (x, y), 25, (1.0), -1) 
            
            # Addiere diesen Klecks zum Gesamtbild
            heatmap_mask += temp_layer

    # ---------- 5. Normalisierung & Post-Processing ----------
    # Skaliere die Werte auf den Bereich 0-255 für die Bilddarstellung
    max_val = np.max(heatmap_mask)
    if max_val > 0:
        heatmap_mask = heatmap_mask / max_val * 255
    
    # Konvertierung zurück in 8-Bit Integer (für OpenCV Bilder)
    heatmap_mask_8bit = np.uint8(heatmap_mask)

    # ---------- 6. Einfärben (False Color Mapping) ----------
    # COLORMAP_JET Verlauf: Blau (kalt) -> Grün -> Gelb -> Rot (heiß)
    heatmap_color = cv2.applyColorMap(heatmap_mask_8bit, cv2.COLORMAP_JET)

    # ---------- 7. Overlay & Export ----------
    # Mischverhältnis: 60% Original-Karte, 40% Heatmap
    final_result = cv2.addWeighted(map_img, 0.6, heatmap_color, 0.4, 0)

    # Ergebnis anzeigen
    cv2.imshow("Heatmap Analyse", final_result)
    print("\n Analyse abgeschlossen.")
    print("   [TASTE DRÜCKEN] um zu speichern und zu beenden.")
    
    cv2.waitKey(0)
    
    output_filename = "heatmap_result.png"
    cv2.imwrite(output_filename, final_result)
    print(f"Gespeichert als '{output_filename}'")
    
    cv2.destroyAllWindows()

if __name__ == "__main__":
    generate_heatmap()
