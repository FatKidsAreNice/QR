# run_web_server.py
"""
Hauptsteuerung / Entry-Point für das Schrank-Inventar-System.

Zweck
-----
Diese Datei orchestriert die administrative Verwaltung des Systems:
1. Persistenz-Check: Initialisiert die SQLite-Datenbank und stellt Tabellen sicher.
2. API-Service: Startet den Flask-Webserver in einem Hintergrund-Thread (Daemon),
   damit externe Anfragen (z.B. vom Scanner) parallel bearbeitet werden können.
3. Mensch-Maschine-Schnittstelle (CLI): Bietet ein blockierendes Terminal-Menü
   für den Administrator, um Stammdaten (Schränke) zu pflegen.

Design-Notizen
--------------
- Threading-Modell: Der Webserver läuft als `daemon=True`. Das garantiert, dass der
  Server-Thread automatisch terminiert wird, sobald der User das CLI-Menü beendet.
- Error-Handling: Die Datenbank-Initialisierung ist in einem Try-Block gekapselt,
  um einen "Graceful Exit" zu ermöglichen, falls die Datei gesperrt ist.
- Interaktivität: Das Menü nutzt eine Endlosschleife, die durch User-Input oder
  KeyboardInterrupt (STRG+C) verlassen werden kann.
"""

import threading
import time
import sys

# Eigene Module (Logik & Datenbank)
from web_server import start_server
from add_schrank import add_new_schrank
from delete_schrank import delete_existing_schrank
from database import DatabaseManager

# Globale Status-Variablen
server_running = False

def start_server_in_thread():
    """
    Startet den Flask-Server asynchron.
    
    Da Flask standardmäßig blockiert, lagern wir ihn in einen Thread aus.
    Daemon=True sorgt dafür, dass dieser Thread nicht das Beenden des Programms verhindert.
    """
    global server_running
    
    if not server_running:
        print("\n[SYSTEM] Starte API-Server im Hintergrund...")
        
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        
        server_running = True
        time.sleep(1) # Kurzes Warten auf Socket-Bindung (UX-Optimierung)
        print("Server aktiv auf http://127.0.0.1:5000")
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
    Hauptablauf.
    
    Schritte:
    1. Datenbank-Initialisierung.
    2. Start des Background-Services (Webserver).
    3. Start der administrativen CLI-Schleife.
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
