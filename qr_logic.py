import json
import time
import math
import os
from datetime import datetime
from config import MEMORY_TOLERANCE, BORDER_MARGIN, MAX_TRACKING_DISTANCE, HISTORY_DURATION, RECOVERY_DISTANCE

# --- NEU: Import der Tracking API ---
from tracking_api import schrank_gesehen, schrank_verloren

class QREntity:
    def __init__(self, uid, content, box, original_start_time=None):
        self.uid = uid          # Dies ist jetzt die ECHTE Datenbank-ID (z.B. 12)
        self.content = content  # Der volle Link
        self.box = box
        self.points = None
        
        if original_start_time:
            self.start_time = original_start_time
        else:
            self.start_time = time.time()
            
        self.first_seen_str = datetime.fromtimestamp(self.start_time).strftime("%Y-%m-%d %H:%M:%S")
        self.last_seen_time = time.time()
        self.missing_frames = 0
        self.active = True

    def update(self, box, points):
        self.box = box
        self.points = points
        self.last_seen_time = time.time()
        self.missing_frames = 0
        self.active = True

    def mark_missing(self):
        self.missing_frames += 1
        self.active = False
    
    def get_duration_string(self):
        elapsed = time.time() - self.start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        return f"{minutes:02}:{seconds:02}"

class QRManager:
    def __init__(self, json_path):
        self.json_path = json_path
        self.entities = {} 
        self.history = {}   
        # self.next_uid brauchen wir nicht mehr, da die ID aus dem QR Code kommt
        
        # Optional: JSON trotzdem initialisieren für Debugging
        self.ensure_json_exists()

    def ensure_json_exists(self):
        if not os.path.exists(self.json_path):
            self.write_json([])

    def write_json(self, data_list):
        try:
            with open(self.json_path, 'w') as f:
                json.dump(data_list, f, indent=4)
        except Exception:
            pass

    def is_in_kill_zone(self, box, img_w, img_h):
        x, y, w, h = box
        if x < BORDER_MARGIN or y < BORDER_MARGIN: return True
        if (x + w) > (img_w - BORDER_MARGIN) or (y + h) > (img_h - BORDER_MARGIN): return True
        return False

    def calculate_distance(self, box1, box2):
        c1_x, c1_y = box1[0] + box1[2]/2, box1[1] + box1[3]/2
        c2_x, c2_y = box2[0] + box2[2]/2, box2[1] + box2[3]/2
        return math.hypot(c2_x - c1_x, c2_y - c1_y)

    def extract_id_from_url(self, content):
        """
        Versucht, die ID aus dem String zu holen.
        Erwartet Format: '.../schrank/12' oder einfach '12'
        """
        try:
            # Wenn es eine URL ist, splitte am '/' und nimm das letzte Element
            if "/" in content:
                possible_id = content.split("/")[-1]
                return int(possible_id)
            else:
                # Wenn es nur eine Zahl ist
                return int(content)
        except ValueError:
            return None

    def process(self, detected_contents, detected_boxes, detected_points, img_w, img_h):
        current_time = time.time()
        
        existing_uids = list(self.entities.keys())
        matched_indices = set()

        # --- 1. NORMALES TRACKING (Frame zu Frame) ---
        for i, new_box in enumerate(detected_boxes):
            new_content = detected_contents[i]
            
            # Versuche ID zu extrahieren
            qr_id = self.extract_id_from_url(new_content)
            if qr_id is None: 
                continue # Kein gültiger QR-Code für unser System

            # Prüfen, ob diese ID bereits aktiv getrackt wird
            if qr_id in self.entities:
                # Update existierende Entity
                self.entities[qr_id].update(new_box, detected_points[i])
                if qr_id in existing_uids:
                    existing_uids.remove(qr_id)
                matched_indices.add(i)

        # --- 2. NEUE OBJEKTE & WIEDERBELEBUNG ---
        for i, new_box in enumerate(detected_boxes):
            if i not in matched_indices:
                new_content = detected_contents[i]
                qr_id = self.extract_id_from_url(new_content)
                
                if qr_id is None: continue

                # Fall A: Ist es im Friedhof (History)? -> WIEDERBELEBUNG
                if qr_id in self.history:
                    old_entity = self.history.pop(qr_id)
                    print(f">>> RESURRECT: ID #{qr_id} ist zurück!")
                    
                    # API AUFRUF: GESEHEN
                    schrank_gesehen(qr_id)

                    resurrected = QREntity(qr_id, new_content, new_box, old_entity.start_time)
                    resurrected.points = detected_points[i]
                    self.entities[qr_id] = resurrected
                
                # Fall B: Ganz neu
                else:
                    print(f">>> NEU ENTDECKT: ID #{qr_id}")
                    
                    # API AUFRUF: GESEHEN
                    schrank_gesehen(qr_id)
                    
                    self.entities[qr_id] = QREntity(qr_id, new_content, new_box)

        # --- 3. VERLORENE OBJEKTE (Aufräumen) ---
        codes_to_move_to_history = []
        
        for uid in existing_uids:
            entity = self.entities[uid]
            entity.mark_missing()
            
            should_remove = False
            
            # Kill-Zone: Sofort raus
            if self.is_in_kill_zone(entity.box, img_w, img_h):
                print(f"<<< RAND-KILL: ID #{uid}")
                should_remove = True
            
            # Timeout
            elif entity.missing_frames > MEMORY_TOLERANCE:
                print(f"<<< TIMEOUT: ID #{uid}")
                should_remove = True

            if should_remove:
                # API AUFRUF: VERLOREN
                schrank_verloren(uid)
                
                codes_to_move_to_history.append(uid)

        for uid in codes_to_move_to_history:
            self.history[uid] = self.entities[uid]
            del self.entities[uid]

        # --- 4. HISTORY CLEANUP ---
        history_to_delete = []
        for uid, entity in self.history.items():
            if (current_time - entity.last_seen_time) > HISTORY_DURATION:
                history_to_delete.append(uid)
        
        for uid in history_to_delete:
            del self.history[uid]

        # --- 5. JSON UPDATE (Optional für GUI) ---
        # Wir behalten das für deine GUI-Anzeige bei
        json_output = []
        for uid, entity in self.entities.items():
            json_output.append({
                "internal_id": uid,
                "content": entity.content,
                "duration": entity.get_duration_string(),
                "timestamp": entity.first_seen_str,
                "status": "LIVE" if entity.active else "MEMORY"
            })
        self.write_json(json_output)
        
        return self.entities
