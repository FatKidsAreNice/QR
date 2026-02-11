# add_schrank.py
from schrank import Schrank
from database import DatabaseManager
from qr_generator import QRCodeGenerator

def add_new_schrank():
    """
    Führt einen Dialog, um einen neuen Schrank zu erstellen.
    Erscheinungs- und Abgangspunkt werden von der Kamera gesetzt.
    """
    print("--- Neuen Schrank hinzufügen ---")
    
    # 1. Nur noch die Ware abfragen
    ware = input("Ware (z.B. 'Platinen V4'): ")
    
    if not ware:
        print("Fehler: 'Ware' darf nicht leer sein. Abbruch.")
        return

    # 2. Schrank-Instanz erstellen
    # Wir übergeben None (NULL) für die Zeit-Felder.
    neuer_schrank = Schrank(ware, erscheinungspunkt=None, abgangspunkt=None)
    
    try:
        # 3. Komponenten initialisieren
        db_manager = DatabaseManager()
        qr_gen = QRCodeGenerator()
        
        # 4. In Datenbank einfügen
        print(f"Füge '{ware}' zur Datenbank hinzu...")
        new_id = db_manager.insert_schrank(neuer_schrank)
        
        if new_id:
            # 5. QR-Code erstellen
            print(f"Erfolgreich mit ID {new_id} gespeichert.")
            filepath = qr_gen.create_qr_for_schrank(new_id)
            print(f"QR-Code erstellt und gespeichert unter: {filepath}")
        else:
            print("Fehler: Konnte Schrank nicht in der Datenbank speichern.")
            
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")

if __name__ == "__main__":
    add_new_schrank()