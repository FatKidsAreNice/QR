# qr_logic.py
"""
Tracking-Logik / QR-Code Lebenszyklus-Management.

Zweck
-----
Diese Klasse verwaltet die Identität und den Status aller erkannten QR-Codes:
1. Identitäts-Management: Extrahiert die Datenbank-ID aus dem QR-Link.
2. Lebenszyklus: Unterscheidet zwischen "Neu", "Aktiv", "Verloren" (Memory) und "Historie" (Friedhof).
3. API-Bridge: Meldet Statusänderungen (Gesehen/Verloren) direkt an die Datenbank-Logik.
4. Persistenz: Schreibt den aktuellen Status in eine JSON-Datei für die GUI.

Design-Notizen
--------------
- Idempotenz: Die ID wird nicht generiert, sondern aus dem QR-Code (URL) gelesen.
- Wiederbelebung (Resurrection): Objekte, die kurz verschwinden und wieder auftauchen, 
  behalten ihre ursprüngliche Startzeit (Session-Dauer läuft weiter).
- Kill-Zone: Objekte am Bildrand werden sofort entfernt, um "Geister-Tracking" beim Hinaustragen zu verhindern.
- API-Trigger: Die Funktionen `schrank_gesehen` und `schrank_verloren` werden ereignisgesteuert aufgerufen.
"""

import json
import time
import math
import os
from datetime import datetime
from config import MEMORY_TOLERANCE, BORDER_MARGIN, MAX_TRACKING_DISTANCE, HISTORY_DURATION, RECOVERY_DISTANCE

# API-Schnittstelle zur Datenbank
from tracking_api import schrank_gesehen, schrank_verloren

class QREntity:
    """Repräsentiert ein einzelnes getracktes Objekt (Schrank)."""
    
    def __init__(self, uid, content, box, original_start_time=None):
        self.uid = uid          # ECHTE Datenbank-ID (z.B. 12)
        self.content = content  # Der volle Link (Raw Data)
        self.box = box
        self.points = None
        
        # Zeit-Management: Bei Wiederbelebung wird die alte Startzeit übernommen
        if original_start_time:
            self.start_time = original_start_time
        else:
            self.start_time = time.time()
            
        self.first_seen_str = datetime.fromtimestamp(self.start_time).strftime("%Y-%m-%d %H:%M:%S")
        self.last_seen_time = time.time()
        self.missing_frames = 0
        self.active = True

    def update(self, box, points):
        """Aktualisiert Position und setzt den Timeout-Counter zurück."""
        self.box = box
        self.points = points
        self.last_seen_time = time.time()
        self.missing_frames = 0
        self.active = True

    def mark_missing(self):
        """Erhöht den Zähler für verpasste Frames (Grace Period)."""
        self.missing_frames += 1
        self.active = False
    
    def get_duration_string(self):
        """Formatiert die Verweildauer als MM:SS String."""
        elapsed = time.time() - self.start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        return f"{minutes:02}:{seconds:02}"

class QRManager:
    def __init__(self, json_path):
        """
        Initialisiert den Manager.
        
        Args:
            json_path: Pfad zur JSON-Datei für den Datenaustausch mit der GUI.
        """
        self.json_path = json_path
        self.entities = {}  # Aktive Objekte (Live + Memory Grace Period)
        self.history = {}   # "Friedhof" für kurzzeitig verlorene Objekte (für Wiederbelebung)
        
        # Sicherstellen, dass die JSON-Datei existiert (verhindert GUI-Fehler)
        self.ensure_json_exists()

    # ---------- Helper Funktionen ----------

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
        """Prüft, ob ein Objekt den Bildrand berührt (Indikator für Verlassen des Bereichs)."""
        x, y, w, h = box
        if x < BORDER_MARGIN or y < BORDER_MARGIN: return True
        if (x + w) > (img_w - BORDER_MARGIN) or (y + h) > (img_h - BORDER_MARGIN): return True
        return False

    def calculate_distance(self, box1, box2):
        """Euklidische Distanz zwischen zwei Box-Mittelpunkten."""
        c1_x, c1_y = box1[0] + box1[2]/2, box1[1] + box1[3]/2
        c2_x, c2_y = box2[0] + box2[2]/2, box2[1] + box2[3]/2
        return math.hypot(c2_x - c1_x, c2_y - c1_y)

    def extract_id_from_url(self, content):
        """
        Parser-Logik: Extrahiert die reine ID aus dem QR-String.
        Erwartet Format: '.../schrank/12' oder einfach '12'.
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

    # ---------- Hauptlogik (Process Loop) ----------

    def process(self, detected_contents, detected_boxes, detected_points, img_w, img_h):
        """
        Verarbeitet einen Frame: Matcht Erkennungen gegen existierende Objekte.
        
        Ablauf:
        1. Update: Aktualisiere bekannte IDs.
        2. Neu/Wiederbelebung: Behandle neue IDs (Check gegen History).
        3. Aufräumen: Prüfe Timeouts und Kill-Zones -> API Calls.
        4. Garbage Collection: Lösche alte History-Einträge.
        5. Export: Schreibe GUI-Daten.
        """
        current_time = time.time()
        
        existing_uids = list(self.entities.keys())
        matched_indices = set()

        # --- 1. NORMALES TRACKING (Frame zu Frame Update) ---
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
                    
                    # API TRIGGER: Status auf "active" setzen
                    schrank_gesehen(qr_id)

                    resurrected = QREntity(qr_id, new_content, new_box, old_entity.start_time)
                    resurrected.points = detected_points[i]
                    self.entities[qr_id] = resurrected
                
                # Fall B: Ganz neu
                else:
                    print(f">>> NEU ENTDECKT: ID #{qr_id}")
                    
                    # API TRIGGER: Status auf "active" setzen
                    schrank_gesehen(qr_id)
                    
                    self.entities[qr_id] = QREntity(qr_id, new_content, new_box)

        # --- 3. VERLORENE OBJEKTE (Aufräumen) ---
        codes_to_move_to_history = []
        
        # Alle IDs, die in DIESEM Frame nicht geupdatet wurden (übrig in existing_uids)
        for uid in existing_uids:
            entity = self.entities[uid]
            entity.mark_missing()
            
            should_remove = False
            
            # Kriterium 1: Kill-Zone (Sofort raus, wenn am Rand verloren)
            if self.is_in_kill_zone(entity.box, img_w, img_h):
                print(f"<<< RAND-KILL: ID #{uid}")
                should_remove = True
            
            # Kriterium 2: Timeout (Zu lange nicht gesehen)
            elif entity.missing_frames > MEMORY_TOLERANCE:
                print(f"<<< TIMEOUT: ID #{uid}")
                should_remove = True

            if should_remove:
                # API TRIGGER: Status auf "inactive" (Abgang) setzen
                schrank_verloren(uid)
                
                codes_to_move_to_history.append(uid)

        # Verschiebe entfernte Objekte in die History (für mögliche Wiederbelebung)
        for uid in codes_to_move_to_history:
            self.history[uid] = self.entities[uid]
            del self.entities[uid]

        # --- 4. HISTORY CLEANUP (Endgültiges Löschen) ---
        history_to_delete = []
        for uid, entity in self.history.items():
            if (current_time - entity.last_seen_time) > HISTORY_DURATION:
                history_to_delete.append(uid)
        
        for uid in history_to_delete:
            del self.history[uid]

        # --- 5. JSON UPDATE (Datenübergabe an GUI) ---
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
