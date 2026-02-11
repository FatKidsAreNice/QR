# run_web_server.py
import threading
import time

# --- Wir importieren die Funktionen aus deinen anderen Dateien ---
from web_server import start_server
from add_schrank import add_new_schrank
from delete_schrank import delete_existing_schrank
from database import DatabaseManager

# --- Globale Variable, um den Server-Status zu speichern ---
# (Wird jetzt nur noch für die Menü-Anzeige gebraucht)
server_running = False
server_thread = None

def main_menu():
    """Zeigt das Hauptmenü an und gibt die Auswahl zurück."""
    print("\n--- 🛠️ Hauptmenü Schrank-Inventar ---")
    
    # Der Server-Status wird jetzt immer 'Läuft' sein,
    # da er am Anfang gestartet wird.
    if server_running:
        print("   (ℹ️ Server-Status: Läuft im Hintergrund)")
    else:
        # Dieser Fall sollte nur kurz beim Start auftreten
        print("   (ℹ️ Server-Status: Startet...)")
        
    print("---------------------------------------")
    print("(1) Neuen Schrank hinzufügen")
    print("(2) Existierenden Schrank löschen")
    print("(3) Programm beenden") # Ehemals (4)
    print("---------------------------------------")
    return input("Bitte wähle eine Option (1-3): ")

def start_server_in_thread():
    """Startet den Server in einem separaten Thread."""
    global server_running, server_thread
    
    # Die 'if not server_running'-Prüfung ist technisch nicht mehr nötig,
    # da wir dies nur einmal aufrufen, aber sie schadet nicht.
    if not server_running:
        print("\nStarte den Web-Server im Hintergrund...")
        
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        
        server_running = True
        time.sleep(1) # Kurze Pause, damit der Server hochfahren kann
        print("✅ Server läuft jetzt auf http://127.0.0.1:5000")
    else:
        print("\nℹ️ Der Server läuft bereits im Hintergrund.")

# --- Das Hauptprogramm ---
if __name__ == "__main__":
    
    # 1. Setup: Sicherstellen, dass die DB-Tabelle existiert
    try:
        db = DatabaseManager()
        db.create_schrank_table()
        print("Datenbank-Tabelle erfolgreich sichergestellt.")
    except Exception as e:
        print(f"FATALER FEHLER: Konnte Datenbank nicht initialisieren: {e}")
        exit()

    # 2. --- AUTOMATISCHER SERVER-START ---
    # Wir rufen den Serverstart *vor* der Menü-Schleife auf.
    start_server_in_thread()

    # 3. Die Hauptmenü-Schleife
    while True:
        choice = main_menu()
        
        if choice == '1':
            # --- Schrank hinzufügen ---
            print("\n---")
            add_new_schrank()
            print("---\n")
            
        elif choice == '2':
            # --- Schrank löschen ---
            print("\n---")
            delete_existing_schrank()
            print("---\n")

        elif choice == '3': # Ehemals (4)
            # --- Beenden ---
            print("Programm wird beendet...")
            break
            
        else:
            print("\n⚠️ Ungültige Eingabe. Bitte eine Zahl von 1 bis 3 wählen.")

    print("Auf Wiedersehen!")