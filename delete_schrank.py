# delete_schrank.py
from database import DatabaseManager
from qr_generator import QRCodeGenerator

def delete_existing_schrank():
    """
    Führt einen Dialog, um einen existierenden Schrank
    anhand seiner ID zu löschen.
    """
    print("--- Schrank löschen ---")
    
    # 1. ID vom Benutzer abfragen
    id_input = input("Welche Schrank-ID soll gelöscht werden? ")
    
    try:
        schrank_id = int(id_input)
    except ValueError:
        print("Fehler: Das ist keine gültige Zahl. Abbruch.")
        return

    # 2. Komponenten initialisieren
    db_manager = DatabaseManager()
    qr_gen = QRCodeGenerator()
    
    try:
        # 3. Zur Sicherheit nach den Daten fragen, bevor wir löschen
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

        # 4. Bestätigung einholen
        confirm = input("Diesen Eintrag wirklich löschen? (ja/nein): ").lower()
        
        if confirm == 'ja':
            # 5. Aus Datenbank löschen
            if db_manager.delete_schrank_by_id(schrank_id):
                print(f"Schrank {schrank_id} erfolgreich aus der Datenbank gelöscht.")
                
                # 6. Zugehörigen QR-Code löschen
                qr_gen.delete_qr_for_schrank(schrank_id)
            else:
                # Sollte nicht passieren, da wir 'get_schrank_by_id' vorher aufgerufen haben
                print(f"Fehler: Schrank {schrank_id} konnte nicht gelöscht werden.")
        else:
            print("Löschvorgang abgebrochen.")

    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")

if __name__ == "__main__":
    delete_existing_schrank()