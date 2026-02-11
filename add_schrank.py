# add_schrank.py
"""
Modul zum Anlegen neuer Warenträger (Stammdaten).

Zweck
-----
Dieses Skript steuert den Prozess der Neuaufnahme eines Schranks/Warenträgers:
1. Datenerfassung: Fragt die Bezeichnung der Ware vom Benutzer ab.
2. Initialisierung: Erstellt ein Schrank-Objekt (zunächst ohne Zeitstempel).
3. Persistierung: Speichert das Objekt in der SQLite-Datenbank und erhält eine eindeutige ID.
4. Artefakt-Generierung: Erzeugt basierend auf der neuen Datenbank-ID automatisch 
   einen QR-Code für den physischen Druck.

Design-Notizen
--------------
- ID-Abhängigkeit: Der QR-Code kann erst generiert werden, NACHDEM der Datenbank-Eintrag 
  erfolgt ist, da die ID (Auto-Increment) im QR-Code kodiert sein muss.
- Tracking-Status: Die Felder 'Erscheinungspunkt' und 'Abgangspunkt' werden hier 
  bewusst mit None (NULL) initialisiert. Diese werden erst später durch die 
  Kamera-Software (Tracking_main.py) gesetzt, sobald der QR-Code im Video-Feed auftaucht.
"""

from schrank import Schrank
from database import DatabaseManager
from qr_generator import QRCodeGenerator

def add_new_schrank():
    """
    Führt den Dialog zur Erstellung eines neuen Datensatzes.
    
    Ablauf:
    Input (Ware) -> DB Insert -> ID Erhalt -> QR-Code Generierung.
    """
    print("\n--- Neuen Schrank registrieren ---")
    
    # ---------- 1. Benutzereingabe (User Input) ----------
    # Wir benötigen nur den Namen der Ware. Tracking-Daten sind noch unbekannt.
    ware = input("Bitte Bezeichnung der Ware eingeben (z.B. 'Kochschinken'): ").strip()
    
    # Validierung: Leere Strings abfangen
    if not ware:
        print("Fehler: Die Bezeichnung darf nicht leer sein. Vorgang abgebrochen.")
        return

    # ---------- 2. Objekt-Initialisierung ----------
    # Wir erzeugen eine Instanz. Zeitstempel sind explizit None.
    neuer_schrank = Schrank(ware, erscheinungspunkt=None, abgangspunkt=None)
    
    try:
        # ---------- 3. Datenbank-Verbindung & Speichern ----------
        db_manager = DatabaseManager()
        
        print(f"Versuche '{ware}' in die Datenbank zu schreiben...")
        new_id = db_manager.insert_schrank(neuer_schrank)
        
        if new_id:
            print(f"Datenbank-Eintrag erfolgreich. Neue ID: {new_id}")
            
            # ---------- 4. QR-Code Generierung ----------
            # Erst jetzt, da wir die ID haben, können wir den Code backen.
            qr_gen = QRCodeGenerator()
            filepath = qr_gen.create_qr_for_schrank(new_id)
            
            print(f"QR-Code generiert und gespeichert: {filepath}")
            print("   (Diesen Code bitte ausdrucken und am Warenträger anbringen)")
            
        else:
            print("Fehler: Konnte Datensatz nicht speichern (Rückgabe war None).")
            
    except Exception as e:
        # Fängt Datenbank-Locks oder Dateisystem-Fehler ab
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")

if __name__ == "__main__":
    # Ermöglicht Standalone-Test dieses Moduls
    add_new_schrank()
