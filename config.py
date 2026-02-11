# config.py
"""
Zentrale Konfiguration für das Track & TrAIce System.

Zweck
-----
Diese Datei bündelt alle statischen Parameter, Pfade und Schwellenwerte.
Änderungen an der Hardware (neue Kamera) oder an der Umgebung (Lichtverhältnisse) können hier angepasst werden, ohne den 
Programmcode ändern zu müssen.

Design-Notizen
--------------
- Pfad-Unabhängigkeit: Wir nutzen `os.path`, um absolute Pfade relativ zur
  Position dieses Skripts zu berechnen. Das macht die Software portabel 
  (z.B. zwischen Dev-Laptop und Jetson Nano).
- Performance-Tuning: Der Parameter `SCALE_FACTOR` ist der wichtigste Hebel 
  für die Framerate (FPS). Kleinerer Faktor = Schneller, aber ungenauer.
"""

import os

# ==========================================
# 1. DATEISYSTEM & PFADE
# ==========================================
# Ermittelt den absoluten Pfad des Ordners, in dem diese Datei liegt.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Datenbank-Datei für persistente QR-Code Zustände (JSON-basiert im Prototyp)
JSON_FILE = os.path.join(BASE_DIR, "active_qrcodes.json")

# Bilddatei des Lager-Layouts für die Vogelperspektive
MAP_FILE = os.path.join(BASE_DIR, "grundriss.png")


# ==========================================
# 2. KAMERA HARDWARE (Treiber-Settings)
# ==========================================
# Native Auflösung des Sensors (hier: Arducam IMX519 / Jetson).
# Achtung: Höhere Auflösung = Mehr Rechenlast für die CPU/GPU.
CAM_WIDTH = 2560   
CAM_HEIGHT = 1440  

# Ziel-Framerate. Wird an GStreamer übergeben.
# Sollte nicht höher sein, als die Belichtungszeit zulässt.
CAM_FPS = 17       


# ==========================================
# 3. COMPUTER VISION & PERFORMANCE
# ==========================================
# Skalierungsfaktor für die Bildverarbeitung.
# 0.5 bedeutet: Wir rechnen auf 1280x720. 
# Das vervierfacht die Geschwindigkeit der QR-Erkennung (pyzbar).
SCALE_FACTOR = 0.5       

# "Kill Zone" am Bildrand [in Pixeln].
# Objekte, die diesen Rand berühren, gelten als "verlassen".
# Verhindert, dass halb abgeschnittene Codes fehlerhaft getrackt werden.
BORDER_MARGIN = 100      


# ==========================================
# 4. TRACKING LOGIK (Verhalten)
# ==========================================
# [Frames] Kurzzeitgedächtnis (Debouncing).
# Wie viele Frames darf ein Code unsichtbar sein (z.B. durch Lichtreflexion),
# bevor er als "verloren" markiert wird?
# 15 Frames bei 17 FPS ~= knapp 1 Sekunde Toleranz.
MEMORY_TOLERANCE = 15       

# [Pixel] Maximale Sprungdistanz pro Frame.
# Wenn sich ein Code weiter als 300px bewegt, wird er als NEUES Objekt betrachtet.
# Verhindert ID-Swapping zwischen zwei schnell passierenden Boxen.
MAX_TRACKING_DISTANCE = 300 


# ==========================================
# 5. RE-IDENTIFIKATION (Wiederbelebung)
# ==========================================
# [Sekunden] Langzeitgedächtnis für verdeckte Objekte.
# Wenn ein Regal kurz verschwindet und < 10s später 
# wieder auftaucht, behält er seine alte ID.
HISTORY_DURATION = 10.0     

# [Pixel] Erweiterter Suchradius für die Wiederbelebung.
# Darf größer sein als MAX_TRACKING_DISTANCE, da in 10 Sekunden 
# eine größere Strecke zurückgelegt werden kann.
RECOVERY_DISTANCE = 500
