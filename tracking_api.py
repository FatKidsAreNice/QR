# tracking_api.py
from database import DatabaseManager
from datetime import datetime

def _get_current_timestamp():
    """Helper-Funktion für einen sauberen Zeitstempel."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def schrank_gesehen(schrank_id):
    """
    Wird vom Kamerasystem aufgerufen, wenn ein QR-Code (wieder) erkannt wird.
    
    Logik:
    1. Wenn 'erscheinungspunkt' leer ist: Setze ihn (erster Scan).
    2. Wenn 'abgangspunkt' gesetzt ist: Leere ihn (der Schrank ist zurück).
    """
    print(f"[Tracking API] GESEHEN: ID {schrank_id}")
    db = DatabaseManager()
    
    # Zuerst die aktuellen Daten des Schranks holen
    current_data = db.get_schrank_by_id(schrank_id)
    if not current_data:
        print(f"[Tracking API] FEHLER: ID {schrank_id} nicht in DB gefunden.")
        return

    is_erster_scan = (current_data['erscheinungspunkt'] is None)
    ist_zurueckgekehrt = (current_data['abgangspunkt'] is not None)

    # Fall 1: Der Schrank wird zum allerersten Mal gesehen
    if is_erster_scan:
        timestamp = _get_current_timestamp()
        db.update_erscheinungszeit(schrank_id, timestamp)
        print(f"[Tracking API] ID {schrank_id} zum ERSTEN Mal erfasst um {timestamp}.")

    # Fall 2: Der Schrank war weg und ist jetzt wieder da
    if ist_zurueckgekehrt:
        # Setze die Abgangszeit zurück auf NULL
        db.update_abgangszeit(schrank_id, None)
        print(f"[Tracking API] ID {schrank_id} ist ZURÜCKgekehrt. Abgangszeit gelöscht.")
        
    if not is_erster_scan and not ist_zurueckgekehrt:
        print(f"[Tracking API] ID {schrank_id} ist bereits als anwesend markiert.")

def schrank_verloren(schrank_id):
    """
    Wird vom Kamerasystem aufgerufen, wenn ein QR-Code nicht mehr gesehen wird.
    
    Logik:
    1. Trägt die Abgangszeit ein, ABER nur, wenn sie noch leer ist.
    """
    print(f"[Tracking API] VERLOREN: ID {schrank_id}")
    db = DatabaseManager()

    # Zuerst die aktuellen Daten des Schranks holen
    current_data = db.get_schrank_by_id(schrank_id)
    if not current_data:
        print(f"[Tracking API] FEHLER: ID {schrank_id} nicht in DB gefunden.")
        return

    # Nur eintragen, wenn er nicht bereits als "verloren" markiert ist
    if current_data['abgangspunkt'] is None:
        timestamp = _get_current_timestamp()
        db.update_abgangszeit(schrank_id, timestamp)
        print(f"[Tracking API] ID {schrank_id} als ABGEGANGEN markiert um {timestamp}.")
    else:
        print(f"[Tracking API] ID {schrank_id} ist bereits als abwesend markiert.")