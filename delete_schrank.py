# delete_schrank.py
"""
Interaktives Skript zum Löschen von Schränken.

Fragt den Nutzer nach einer Schrank-ID, zeigt die gefundenen Daten zur 
Kontrolle an und löscht (nach einer Sicherheitsabfrage) sowohl den Eintrag 
aus der SQLite-Datenbank als auch das dazugehörige QR-Code-Bild vom PC.
"""

from database import DatabaseManager
from qr_generator import QRCodeGenerator

def delete_existing_schrank():
    """
    Führt den kompletten Lösch-Dialog durch.
    
    Holt zuerst den Datensatz zur Vorschau aus der DB, um versehentliche 
    Löschungen zu vermeiden. Erst nach expliziter Bestätigung mit 'ja' 
    werden der DB-Eintrag und die physische QR-Code-Datei entfernt.
    """
    print("--- Schrank löschen ---")
    
    # ---------- 1. Benutzereingabe ----------
    id_input = input("Welche Schrank-ID soll gelöscht werden? ")
    
    try:
        schrank_id = int(id_input)
    except ValueError:
        print("Fehler: Das ist keine gültige Zahl. Abbruch.")
        return

    # ---------- 2. Ressourcen-Initialisierung ----------
    db_manager = DatabaseManager()
    qr_gen = QRCodeGenerator()
    
    try:
        # ---------- 3. Verifikation (Lookup) ----------
        schrank_data = db_manager.get_schrank_by_id(schrank_id)
        
        if not schrank_data:
            print(f"Fehler: Ein Schrank mit der ID {schrank_id} wurde nicht gefunden.")
            return
            
        print("\n--- Folgender Schrank wird gelöscht ---")
        print(f" ID: {schrank_data['id']}")
        print(f" Ware: {schrank_data['ware']}")
        print(f" Erschien: {schrank_data['erscheinungspunkt']}")
        print(f" Abgang: {schrank_data['abgangspunkt']}")
        print("---------------------------------------")

        # ---------- 4. Sicherheitsabfrage ----------
        confirm = input("Diesen Eintrag wirklich löschen? (ja/nein): ").lower()
        
        if confirm == 'ja':
            # ---------- 5. Datenbank-Bereinigung ----------
            if db_manager.delete_schrank_by_id(schrank_id):
                print(f"Schrank {schrank_id} erfolgreich aus der Datenbank gelöscht.")
                
                # ---------- 6. Dateisystem-Bereinigung ----------
                # Löscht das physische PNG-Bild, um Speicherplatz freizugeben
                qr_gen.delete_qr_for_schrank(schrank_id)
            else:
                # Fallback: Sollte theoretisch nicht erreicht werden, da Check oben erfolgreich war
                print(f"Fehler: Schrank {schrank_id} konnte nicht gelöscht werden.")
        else:
            print("Löschvorgang abgebrochen.")

    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")

if __name__ == "__main__":
    delete_existing_schrank()

