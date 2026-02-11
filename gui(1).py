import cv2
import numpy as np
from config import BORDER_MARGIN

# --- ALTE FUNKTIONEN (FÜR KAMERA VIEW) ---

def draw_overlay(frame, width, height, active_entities):
    # A) Roter Kill-Zone Rahmen
    cv2.rectangle(frame, 
                  (BORDER_MARGIN, BORDER_MARGIN), 
                  (width - BORDER_MARGIN, height - BORDER_MARGIN), 
                  (0, 0, 255), 3)
    cv2.putText(frame, "EXIT ZONE", (10, BORDER_MARGIN - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # B) Entities zeichnen
    for entity in active_entities.values():
        draw_entity(frame, entity)

    # C) Info Text
    cv2.putText(frame, f"Objects: {len(active_entities)}", (30, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
    cv2.putText(frame, f"Res: {width}x{height}", (30, height - 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

def draw_entity(frame, entity):
    x, y, w, h = entity.box
    color = (0, 255, 0) if entity.active else (0, 165, 255)
    thickness = 4 if entity.active else 2
    
    # Box / Polygon zeichnen
    if entity.points is not None and len(entity.points) == 4:
        cv2.polylines(frame, [entity.points], True, color, thickness)
        tx, ty = entity.points[0][0][0], entity.points[0][0][1] - 10
    else:
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
        tx, ty = x, y - 10

    # Text vorbereiten
    text_line1 = f"Schrank Nr.{entity.uid}"
    text_line2 = f"Time: {entity.get_duration_string()}"
    if not entity.active:
        text_line1 += " (?)"

    # Text zeichnen (Zeile 1: ID)
    cv2.putText(frame, text_line1, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 8)
    cv2.putText(frame, text_line1, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    
    # Text zeichnen (Zeile 2: Timer)
    cv2.putText(frame, text_line2, (tx, ty - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 6)
    cv2.putText(frame, text_line2, (tx, ty - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

# --- NEUE FUNKTION (FÜR GRUNDRISS VIEW MIT TIMER) ---

def draw_map_view(map_img, active_entities, transformation_matrix):
    """
    Zeichnet die Positionen UND die Zeit auf den Grundriss.
    """
    # Kopie erstellen
    display_img = map_img.copy()
    
    h_map, w_map = display_img.shape[:2]

    # Info Text oben links
    cv2.putText(display_img, f"Aktive Objekte: {len(active_entities)}", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

    for entity in active_entities.values():
        if not entity.active:
            continue 

        # 1. Position berechnen
        x, y, w, h = entity.box
        center_x = x + w / 2
        center_y = y + h # Fußpunkt nehmen
        
        # 2. Transformieren
        cam_point = np.array([[[center_x, center_y]]], dtype=np.float32)
        
        try:
            map_point = cv2.perspectiveTransform(cam_point, transformation_matrix)
            mx = int(map_point[0][0][0])
            my = int(map_point[0][0][1])

            # 3. Zeichnen (wenn im Bild)
            if 0 <= mx < w_map and 0 <= my < h_map:
                # Punkt malen
                cv2.circle(display_img, (mx, my), 15, (0, 0, 255), -1) 
                cv2.circle(display_img, (mx, my), 15, (0, 0, 0), 2)
                
                # --- TEXTE ---
                # Zeile 1: ID
                label_id = f"ID {entity.uid}"
                cv2.putText(display_img, label_id, (mx + 20, my), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                
                # Zeile 2: ZEIT (NEU!)
                # Wir holen den Zeit-String (z.B. "00:12")
                label_time = entity.get_duration_string()
                # Wir zeichnen ihn etwas unterhalb der ID (my + 25)
                cv2.putText(display_img, label_time, (mx + 20, my + 25), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 150), 2) # Dunkelrot

        except Exception as e:
            print(f"Transform Error: {e}")

    return display_img
