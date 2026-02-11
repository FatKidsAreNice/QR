# gui.py
"""
Visualisierungs-Modul / Grafische Oberfläche.

Zweck
-----
Diese Datei ist verantwortlich für alle grafischen Ausgaben (Rendering):
1. Kamera-Overlay (AR-View): Zeichnet Bounding-Boxen, IDs und Status-Infos direkt in den Video-Feed.
2. Karten-Ansicht (Map-View): Projiziert die Positionen der Objekte auf einen 2D-Grundriss.
3. Text-Rendering: Sorgt für lesbare Informationen (Outlined Text) und Debug-Daten (FPS, Auflösung).

Design-Notizen
--------------
- Zustandslosigkeit: Die Funktionen zeichnen immer den aktuellen Frame neu (Immediate Mode GUI).
- Trennung von Daten und Ansicht: Erhält nur die reinen Datenobjekte (Entities) und kümmert sich um Farben/Formen.
- Fehlertoleranz: Die Karten-Projektion fängt Transformationsfehler ab, falls ein Objekt außerhalb des definierten Bereichs liegt.
"""

import cv2
import numpy as np
from config import BORDER_MARGIN

# ---------- 1. Kamera-Ansicht (Augmented Reality) ----------

def draw_overlay(frame, width, height, active_entities):
    """
    Hauptfunktion für das Zeichnen auf dem Kamerabild.
    Fügt die 'Kill-Zone', alle erkannten Objekte und globale Status-Texte hinzu.
    """
    # A) Roter Kill-Zone Rahmen (Definiert den Bereich, in dem Tracking aktiv ist)
    cv2.rectangle(frame, 
                  (BORDER_MARGIN, BORDER_MARGIN), 
                  (width - BORDER_MARGIN, height - BORDER_MARGIN), 
                  (0, 0, 255), 3)
    cv2.putText(frame, "EXIT ZONE", (10, BORDER_MARGIN - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # B) Entities zeichnen (Iteriert über alle getrackten Objekte)
    for entity in active_entities.values():
        draw_entity(frame, entity)

    # C) Globale Info-Texte (HUD)
    cv2.putText(frame, f"Objects: {len(active_entities)}", (30, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
    cv2.putText(frame, f"Res: {width}x{height}", (30, height - 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

def draw_entity(frame, entity):
    """
    Hilfsfunktion: Zeichnet ein einzelnes Objekt inkl. Box, ID und Zeitstempel.
    Unterscheidet visuell zwischen aktiven (Grün) und inaktiven (Orange) Objekten.
    """
    x, y, w, h = entity.box
    
    # Farbwahl: Grün = Aktiv (im Bild), Orange = Inaktiv (verloren/verdeckt)
    color = (0, 255, 0) if entity.active else (0, 165, 255)
    thickness = 4 if entity.active else 2
    
    # Geometrie zeichnen (Bevorzugt Polygon wenn verfügbar, sonst Rechteck)
    if entity.points is not None and len(entity.points) == 4:
        cv2.polylines(frame, [entity.points], True, color, thickness)
        # Text-Position über dem ersten Punkt
        tx, ty = entity.points[0][0][0], entity.points[0][0][1] - 10
    else:
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
        # Text-Position über der Bounding Box
        tx, ty = x, y - 10

    # Text-Inhalte vorbereiten
    text_line1 = f"Schrank Nr.{entity.uid}"
    text_line2 = f"Time: {entity.get_duration_string()}"
    if not entity.active:
        text_line1 += " (?)"

    # Text-Rendering mit Outline (Schwarzer Rand für bessere Lesbarkeit auf hellem Grund)
    # Zeile 1: ID
    cv2.putText(frame, text_line1, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 8)   # Outline
    cv2.putText(frame, text_line1, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)       # Text
    
    # Zeile 2: Timer
    cv2.putText(frame, text_line2, (tx, ty - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 6) # Outline
    cv2.putText(frame, text_line2, (tx, ty - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2) # Text

# ---------- 2. Grundriss-Ansicht (Top-Down Map) ----------

def draw_map_view(map_img, active_entities, transformation_matrix):
    """
    Projiziert die Kamerapositionen auf einen statischen Grundriss.
    
    Argumente:
    - map_img: Das Hintergrundbild des Raumes.
    - transformation_matrix: Die Homographie-Matrix für die Perspektiv-Transformation.
    """
    # Kopie erstellen, um das Original-Bild nicht zu übermalen
    display_img = map_img.copy()
    
    h_map, w_map = display_img.shape[:2]

    # Info Text oben links im Kartenfenster
    cv2.putText(display_img, f"Aktive Objekte: {len(active_entities)}", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

    for entity in active_entities.values():
        if not entity.active:
            continue 

        # 1. Fußpunkt berechnen (Mitte unten der Bounding Box)
        # Das ist physikalisch der Punkt, wo das Objekt den Boden berührt.
        x, y, w, h = entity.box
        center_x = x + w / 2
        center_y = y + h 
        
        # 2. Transformation (Kamera-Koordinaten -> Karten-Koordinaten)
        cam_point = np.array([[[center_x, center_y]]], dtype=np.float32)
        
        try:
            map_point = cv2.perspectiveTransform(cam_point, transformation_matrix)
            mx = int(map_point[0][0][0])
            my = int(map_point[0][0][1])

            # 3. Zeichnen (nur wenn der Punkt innerhalb der Kartengrenzen liegt)
            if 0 <= mx < w_map and 0 <= my < h_map:
                # Punkt markieren (Roter Punkt mit schwarzem Rand)
                cv2.circle(display_img, (mx, my), 15, (0, 0, 255), -1) 
                cv2.circle(display_img, (mx, my), 15, (0, 0, 0), 2)
                
                # --- Beschriftung ---
                # Zeile 1: ID
                label_id = f"ID {entity.uid}"
                cv2.putText(display_img, label_id, (mx + 20, my), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                
                # Zeile 2: ZEIT (Visualisierung der Verweildauer)
                label_time = entity.get_duration_string()
                cv2.putText(display_img, label_time, (mx + 20, my + 25), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 150), 2) # Dunkelrot

        except Exception as e:
            print(f"Transform Error: {e}")

    return display_img
