import time
import signal
import cv2
import numpy as np
import argparse
from pyzbar.pyzbar import decode
from collections import deque # Für den Tracer-Schweif

# Eigene Module
import config
from qr_logic import QRManager
from gui import draw_overlay, draw_map_view 
from database import DatabaseManager 

# Hardware Treiber
from JetsonCamera import Camera
from Focuser import Focuser
from Autofocus import FocusState, doFocus

exit_ = False

def sigint_handler(signum, frame):
    global exit_
    exit_ = True

signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)

def parse_cmdline():
    parser = argparse.ArgumentParser(description='Arducam Modular QR System')
    parser.add_argument('-i', '--i2c-bus', type=int, required=True, help='I2C Bus (9 for Orin)')
    return parser.parse_args()

def get_calibration_matrix():
    # 1. KAMERA-PUNKTE (Quelle)
    src_points = np.float32([
        [634,  120],    [2086, 150],
        [2104, 1296],   [600,  1302]
    ])
    # 2. GRUNDRISS-PUNKTE (Ziel)
    dst_points = np.float32([
        [30,   38],     [765,  38],
        [766,  844],    [29,   847]
    ])
    return cv2.getPerspectiveTransform(src_points, dst_points)

def transform_point(x, y, matrix):
    """Hilfsfunktion: Rechnet einen einzelnen Punkt um."""
    pt = np.array([[[x, y]]], dtype=np.float32)
    t_pt = cv2.perspectiveTransform(pt, matrix)
    return int(t_pt[0][0][0]), int(t_pt[0][0][1])

def main():
    print("\n--- STARTE TRACKING MIT LOGGING & TRACER ---\n")
    args = parse_cmdline()
    
    # DB Init
    db = DatabaseManager()
    db.create_schrank_table()
    db.create_movement_table() # NEU: Tabelle für Koordinaten

    # Hardware Init
    try:
        camera = Camera(width=config.CAM_WIDTH, height=config.CAM_HEIGHT)
    except Exception as e:
        print(f"Kamera Fehler: {e}")
        return

    focuser = Focuser(args.i2c_bus)
    try: focuser.set(Focuser.OPT_FOCUS, 2000)
    except: pass
    focusState = FocusState()

    # Map laden
    try:
        map_img = cv2.imread(config.MAP_FILE)
    except:
        import os
        map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grundriss.png")
        map_img = cv2.imread(map_path)

    if map_img is None:
        print("FEHLER: grundriss.png nicht gefunden!")
        return

    map_h, map_w = map_img.shape[:2]
    matrix = get_calibration_matrix()

    print("Warte auf Kamera...")
    time.sleep(2)
    qr_manager = QRManager(config.JSON_FILE)

    window_name = "Lagerbestand Tracking"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

    # --- STATE VARIABLES ---
    show_map_view = True
    show_tracer = True      # Standardmäßig an?
    
    # Logging Timer
    last_log_time = time.time()
    LOG_INTERVAL = 5.0 # Sekunden

    # Tracer Speicher (Dictionary: ID -> Deque von Punkten)
    # Wir speichern die letzten 50 Punkte pro Schrank für den visuellen Schweif
    trails = {} 

    print("System bereit.")
    print(" [TAB] Ansicht | [T] Tracer An/Aus | [F] Fokus | [Q] Ende")

    while not exit_:
        frame = camera.getFrame(2000)
        if frame is None: continue

        frame = cv2.rotate(frame, cv2.ROTATE_180)
        height, width = frame.shape[:2]
        
        # Erkennung
        small_frame = cv2.resize(frame, (0, 0), fx=config.SCALE_FACTOR, fy=config.SCALE_FACTOR)
        decoded_objects = decode(cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY))
        
        found_codes = []
        found_boxes = []
        found_points = []
        inv_scale = 1.0 / config.SCALE_FACTOR

        for obj in decoded_objects:
            qr_data = obj.data.decode('utf-8')
            (x, y, w, h) = obj.rect
            box = (int(x*inv_scale), int(y*inv_scale), int(w*inv_scale), int(h*inv_scale))
            
            pts = []
            for p in obj.polygon: pts.append([int(p.x*inv_scale), int(p.y*inv_scale)])
            np_pts = np.array(pts, dtype=np.int32).reshape((-1, 1, 2)) if pts else None

            found_codes.append(qr_data)
            found_boxes.append(box)
            found_points.append(np_pts)

        active_entities = qr_manager.process(found_codes, found_boxes, found_points, width, height)

        # --- LOGIK: LOGGING & TRACER ---
        current_time = time.time()
        should_log = (current_time - last_log_time) >= LOG_INTERVAL

        for uid, entity in active_entities.items():
            if not entity.active: continue

            # Mittelpunkt im Kamerabild berechnen
            bx, by, bw, bh = entity.box
            cam_cx, cam_cy = bx + bw/2, by + bh

            # Umrechnen auf Karte
            try:
                map_x, map_y = transform_point(cam_cx, cam_cy, matrix)
                
                # A) TRACER UPDATE (Visuell)
                if uid not in trails:
                    trails[uid] = deque(maxlen=50) # Schweif Länge 50 Punkte
                trails[uid].append((map_x, map_y))

                # B) DATABASE LOGGING (Alle 5 Sekunden)
                if should_log:
                    # Prüfen ob Punkt im Bild ist
                    if 0 <= map_x < map_w and 0 <= map_y < map_h:
                        db.log_movement(uid, map_x, map_y)
                        print(f"[LOG] ID {uid} bei {map_x}/{map_y} gespeichert.")

            except Exception as e:
                pass # Fehler bei Transformation ignorieren

        if should_log:
            last_log_time = current_time

        # --- ZEICHNEN ---
        if show_map_view:
            final_image = draw_map_view(map_img, active_entities, matrix)
            
            # TRACER AUF KARTE ZEICHNEN
            if show_tracer:
                for uid, trail in trails.items():
                    # Nur zeichnen, wenn der Schrank gerade aktiv ist (optional)
                    if uid in active_entities and active_entities[uid].active:
                        # Punkte verbinden
                        pts = np.array(trail, np.int32)
                        pts = pts.reshape((-1, 1, 2))
                        cv2.polylines(final_image, [pts], False, (255, 0, 0), 2) # Blaue Linie
        else:
            draw_overlay(frame, width, height, active_entities)
            final_image = frame

        cv2.imshow(window_name, final_image)
        
        # Input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'): break
        elif key == 9: show_map_view = not show_map_view
        elif key == ord('f'): 
            focusState.reset()
            doFocus(camera, focuser, focusState)
        elif key == ord('t'): # Toggler für Tracer
            show_tracer = not show_tracer
            print(f"Tracer ist nun {'AN' if show_tracer else 'AUS'}")
        elif key == ord('l'): # Manuelles Loggen erzwingen
            last_log_time = 0 

    camera.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
