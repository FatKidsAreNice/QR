# DB_main.py
"""
Hauptsteuerung / Entry-Point für das Schrank-Inventar-System.

Dieses Skript startet das komplette System:
1. Prüft/erstellt die SQLite-Datenbank.
2. Startet den Flask-Webserver im Hintergrund (Daemon-Thread), 
   damit parallel QR-Scans vom Handy verarbeitet werden können.
3. Öffnet das CLI-Menü zur Verwaltung der Schränke.

Architektur-Hinweis:
Der Server-Thread wird automatisch beendet, sobald das Hauptmenü 
geschlossen wird (entweder über die Menüauswahl oder per STRG+C).
"""

import threading
import time
import sys
import socket

# Eigene Module (Logik & Datenbank)
from web_server import start_server
from add_schrank import add_new_schrank
from delete_schrank import delete_existing_schrank
from database import DatabaseManager

# Globale Status-Variablen
server_running = False

def get_local_ip():
    """Ermittelt die echte WLAN/LAN IPv4-Adresse des Rechners."""
    try:
        # Baut eine Dummy-Verbindung auf
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # Fallback, falls der PC gar kein Netzwerk hat
        return "127.0.0.1"

def start_server_in_thread():
    """
    Startet den Flask-Server in einem separaten Hintergrund-Thread.
    
    Das ist nötig, da app.run() blockiert. Durch daemon=True wird 
    sichergestellt, dass der Server das Beenden des Hauptprogramms 
    nicht blockiert.
    """
    global server_running
    
    if not server_running:
        print("\n[SYSTEM] Starte API-Server im Hintergrund...")
        
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        
        server_running = True
        time.sleep(1) # Kurzes Warten auf Socket-Bindung (UX-Optimierung)
        
        # NEU: Dynamische IP ermitteln und anzeigen
        wlan_ip = get_local_ip()
        print(f"Server aktiv!")
        print(f"-> Lokal (nur dieser PC): http://127.0.0.1:5000")
        print(f"-> Netzwerk (für QR-Codes): http://{wlan_ip}:5000")
    else:
        print("[INFO] Server läuft bereits.")

def main_menu():
    """Rendert das CLI-Menü und fängt die Benutzerwahl ab."""
    print("\n--- Hauptmenü Schrank-Inventar ---")
    
    print(f"   (Status API-Server: Läuft im Hintergrund)")
        
    print("---------------------------------------")
    print("(1) Neuen Schrank anlegen")
    print("(2) Existierenden Schrank löschen")
    print("(3) Programm beenden")
    print("---------------------------------------")
    return input("Bitte wählen (1-3): ")

def main():
   """
    Hauptablauf: Initialisiert die Datenbank, startet den Webserver 
    und ruft abschließend die Endlosschleife für das CLI-Menü auf.
    """
    print("\n--- STARTE INVENTAR-MANAGEMENT SYSTEM ---\n")

    # ---------- 1. Persistenz-Layer Initialisierung ----------
    try:
        db = DatabaseManager()
        db.create_schrank_table()
        print("[INIT] Datenbank-Integrität geprüft.")
    except Exception as e:
        print(f"FATAL: Datenbankfehler: {e}")
        sys.exit(1)

    # ---------- 2. Service-Layer (API) Start ----------
    # Wir starten den Server VOR der Menü-Schleife, damit das System erreichbar ist.
    start_server_in_thread()

    # ---------- 3. User-Interface Loop (CLI) ----------
    while True:
        try:
            choice = main_menu()
            
            if choice == '1':
                # Sub-Prozess: Datensatz anlegen
                print("\n--- Modus: Hinzufügen ---")
                add_new_schrank()
                print("-------------------------\n")
                
            elif choice == '2':
                # Sub-Prozess: Datensatz entfernen
                print("\n--- Modus: Löschen ---")
                delete_existing_schrank()
                print("----------------------\n")

            elif choice == '3':
                # Graceful Shutdown
                print("\n[SYSTEM] Fahre System herunter...")
                break
                
            else:
                print("\n--- Ungültige Eingabe.")
        
        except KeyboardInterrupt:
            # Fängt STRG+C ab für sauberes Beenden
            print("\n\n[SYSTEM] Abbruch durch Benutzer.")
            break

    print("Auf Wiedersehen!")

if __name__ == "__main__":
    main()

