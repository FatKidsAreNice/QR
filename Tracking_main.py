# tracking_main.py
"""
Hauptsteuerung / Entry-Point für das Track & TrAIce System.

Zweck
-----
Diese Datei orchestriert die Erfassung und Verfolgung von Warenträgern:
1. Hardware-Initialisierung: Startet die Jetson-Kamera und den Fokus-Motor.
2. Perception-Pipeline: Liest QR-Codes aus und ordnet sie physischen Objekten zu.
3. Mapping-Logik: Transformiert 2D-Kamerakoordinaten mittels Homographie in 
   reale Lager-Koordinaten (Vogelperspektive).
4. Persistenz: Speichert Bewegungsdaten effizient in einer SQLite-Datenbank.
5. Visualisierung: Zeichnet Live-Positionen auf den Grundriss oder das Kamerabild.

Design-Notizen
--------------
- Soft Real-Time: Der Loop läuft so schnell wie möglich. Datenbank-Schreibvorgänge 
  sind jedoch gethrottled (z.B. alle 5 Sek), um IO-Blocking zu vermeiden.
- Koordinaten-Transformation: Nutzt `cv2.perspectiveTransform` mit einer festen 
  Kalibrierungsmatrix, um die perspektivische Verzerrung der Kamera auszugleichen.
- Robustheit: Fehlende Hardware oder fehlende Map-Dateien werden abgefangen, 
  um einen Absturz des Systems zu verhindern.
"""

import time
import signal
import cv2
import numpy as np
import argparse
import sys
from pyzbar.pyzbar import decode
from collections import deque

# Eigene Module (Architektur-Schichten)
import config
from qr_logic import QRManager
from gui import draw_overlay, draw_map_view 
from database import DatabaseManager 

# Hardware-Treiber
from JetsonCamera import Camera
from Focuser import Focuser
from Autofocus import FocusState, doFocus

# Globale Variable für den sauberen Abbruch
exit_ = False

def sigint_handler(signum, frame):
    """Fängt Systemsignale (STRG+C) ab, um Ressourcen sauber zu schließen."""
    global exit_
    exit_ = True

signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)

def parse_cmdline():
    """Verarbeitet Kommandozeilenargumente."""
    parser = argparse.ArgumentParser(description='Track & TrAIce - Main Loop')
    parser.add_argument('-i', '--i2c-bus', type=int, required=True, help='I2C Bus ID (meist 9 für Jetson Orin/Nano)')
    return parser.parse_args()

def get_calibration_matrix():
    """
    Erstellt die Transformationsmatrix für die Umrechnung von Kamera- zu Kartenkoordinaten.
    
    Hinweis: Diese Punkte sind spezifisch für die aktuelle Kamera-Montageposition.
    Sollte idealerweise in eine externe JSON/YAML-Config ausgelagert werden.
    """
    # 1. Quell-Punkte (Im Kamerabild, verzerrt)
    src_points = np.float32([
        [634,  120],    [2086, 150],
        [2104, 1296],   [600,  1302]
    ])
    # 2. Ziel-Punkte (Auf dem 2D-Grundriss, entzerrt)
    dst_points = np.float32([
        [30,   38],     [765,  38],
        [766,  844],    [29,   847]
    ])
    return cv2.getPerspectiveTransform(src_points, dst_points)

def transform_point(x, y, matrix):
    """
    Wendet die Perspektiv-Transformation auf einen einzelnen Punkt an.
    Returns: (x, y) auf der Karte.
    """
    pt = np.array([[[x, y]]], dtype=np.float32)
    t_pt = cv2.perspectiveTransform(pt, matrix)
    return int(t_pt[0][0][0]), int(t_pt[0][0][1])

def main():
    """
    Initialisierung und Hauptschleife.
    
    Ablauf:
    1. Setup von Datenbank und Hardware.
    2. Laden der Mapping-Ressourcen (Grundriss & Matrix).
    3. Endlosschleife:
       - Frame holen -> QR-Scan -> Koordinaten-Mapping -> DB-Log -> GUI-Update.
    """
    print("\n--- STARTE TRACKING MIT LOGGING & TRACER ---\n")
    args = parse_cmdline()
    
    # ---------- 1. Persistenz-Schicht (Datenbank) ----------
    try:
        db = DatabaseManager()
        db.create_schrank_table()
        db.create_movement_table() 
        print("[INIT] Datenbank verbunden und Tabellen geprüft.")
    except Exception as e:
        print(f"FATAL: Datenbankfehler: {e}")
        sys.exit(1)

    # ---------- 2. Hardware-Schicht Initialisierung ----------
    try:
        # Kamera initialisieren (GStreamer Pipeline intern)
        camera = Camera(width=config.CAM_WIDTH, height=config.CAM_HEIGHT)
    except Exception as e:
        print(f"FATAL: Kamera konnte nicht gestartet werden: {e}")
        return

    # Fokus-Motor Setup (I2C)
    focuser = Focuser(args.i2c_bus)
    try: focuser.set(Focuser.OPT_FOCUS, 2000)
    except: pass
    focusState = FocusState()

    # ---------- 3. Lokalisierungs-Logik (Mapping) ----------
    try:
        map_img = cv2.imread(config.MAP_FILE)
    except:
        # Fallback: Versuche Datei im relativen Pfad zu finden
        import os
        map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grundriss.png")
        map_img = cv2.imread(map_path)

    if map_img is None:
        print("FEHLER: 'grundriss.png' nicht gefunden! Mapping wird fehlschlagen.")
        return

    map_h, map_w = map_img.shape[:2]
    matrix = get_calibration_matrix()
    
    print("[INIT] Warte auf Kamera-Einpegelung...")
    time.sleep(2)
    
    qr_manager = QRManager(config.JSON_FILE)

    # Setup GUI-Fenster
    window_name = "Lagerbestand Tracking"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

    # --- Laufzeit-Variablen (State) ---
    show_map_view = True
    show_tracer = True      
    
    # Logging-Timer (Throttling, um DB nicht zu überfluten)
    last_log_time = time.time()
    LOG_INTERVAL = 5.0 # Sekunden

    # Tracer-Speicher: Dictionary {ID -> Deque(Punkte)}
    # Speichert den Verlauf (Schweif) der letzten Bewegungen
    trails = {} 

    print("System bereit.")
    print(" [TAB] Ansicht wechseln | [T] Tracer An/Aus | [F] Autofokus | [Q] Beenden")

    # ========== Hauptschleife (Main Loop) ==========
    while not exit_:
        # 1. Bildakquise (Frame Grabbing)
        frame = camera.getFrame(2000)
        if frame is None: continue

        # Drehung je nach Montage (180 Grad)
        frame = cv2.rotate(frame, cv2.ROTATE_180)
        height, width = frame.shape[:2]
        
        # 2. Perzeption (Wahrnehmung & Detektion)
        # Downscaling beschleunigt die QR-Erkennung massiv
        small_frame = cv2.resize(frame, (0, 0), fx=config.SCALE_FACTOR, fy=config.SCALE_FACTOR)
        decoded_objects = decode(cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY))
        
        found_codes = []
        found_boxes = []
        found_points = []
        inv_scale = 1.0 / config.SCALE_FACTOR

        for obj in decoded_objects:
            qr_data = obj.data.decode('utf-8')
            (x, y, w, h) = obj.rect
            
            # Koordinaten auf Originalgröße hochskalieren
            box = (int(x*inv_scale), int(y*inv_scale), int(w*inv_scale), int(h*inv_scale))
            
            pts = []
            for p in obj.polygon: pts.append([int(p.x*inv_scale), int(p.y*inv_scale)])
            np_pts = np.array(pts, dtype=np.int32).reshape((-1, 1, 2)) if pts else None

            found_codes.append(qr_data)
            found_boxes.append(box)
            found_points.append(np_pts)

        # 3. Logik-Verarbeitung (Tracking State Update)
        # Verknüpft rohe Scans mit Objekt-IDs (Entprellung/Debouncing)
        active_entities = qr_manager.process(found_codes, found_boxes, found_points, width, height)

        # 4. Transformation & Logging (Mapping & Datenbank)
        current_time = time.time()
        should_log = (current_time - last_log_time) >= LOG_INTERVAL

        for uid, entity in active_entities.items():
            if not entity.active: continue

            # Geometrischer Mittelpunkt der Box berechnen
            bx, by, bw, bh = entity.box
            cam_cx, cam_cy = bx + bw/2, by + bh # Fußpunkt (unten mitte) ist oft genauer

            # Koordinaten-Transformation (Kamera -> Karte)
            try:
                map_x, map_y = transform_point(cam_cx, cam_cy, matrix)
                
                # A) Visualisierungspfad (Tracer) aktualisieren
                if uid not in trails:
                    trails[uid] = deque(maxlen=50) # Maximale Schweif-Länge
                trails[uid].append((map_x, map_y))

                # B) Datenbank-Logging (Zeitgesteuert)
                if should_log:
                    # Plausibilitätscheck: Ist Punkt auf der Karte?
                    if 0 <= map_x < map_w and 0 <= map_y < map_h:
                        db.log_movement(uid, map_x, map_y)
                        print(f"[LOG] ID {uid} -> Pos: {map_x}/{map_y}")

            except Exception as e:
                pass # Transformationsfehler ignorieren (Punkt außerhalb)

        if should_log:
            last_log_time = current_time

        # 5. Visualisierung (GUI Rendering)
        if show_map_view:
            final_image = draw_map_view(map_img, active_entities, matrix)
            
            # Tracer (Schweif) einzeichnen
            if show_tracer:
                for uid, trail in trails.items():
                    # Nur zeichnen, wenn Objekt aktiv ist
                    if uid in active_entities and active_entities[uid].active:
                        pts = np.array(trail, np.int32).reshape((-1, 1, 2))
                        cv2.polylines(final_image, [pts], False, (255, 0, 0), 2) 
        else:
            draw_overlay(frame, width, height, active_entities)
            final_image = frame

        cv2.imshow(window_name, final_image)
        
        # 6. User Input Handling
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'): break
        elif key == 9: # TAB-Taste
            show_map_view = not show_map_view
        elif key == ord('f'): 
            print("[CMD] Autofokus angefordert...")
            focusState.reset()
            doFocus(camera, focuser, focusState)
        elif key == ord('t'): 
            show_tracer = not show_tracer
            print(f"[CMD] Tracer: {'AN' if show_tracer else 'AUS'}")
        elif key == ord('l'): 
            last_log_time = 0 # Erzwingt sofortiges Loggen beim nächsten Frame

    # Aufräumen (Resource Cleanup)
    print("[SYSTEM] Beende Kamera und Fenster...")
    camera.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
