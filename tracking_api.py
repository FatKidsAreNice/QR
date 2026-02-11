# tracking_api.py
"""
Schnittstelle Tracking <-> Datenbank.

Zweck
-----
Diese Datei fungiert als Brücke zwischen der Computer-Vision-Logik und der Datenbank:
1. Event-Handling: Übersetzt technische Ereignisse ("QR erkannt", "QR verloren") in fachliche Status-Updates.
2. Zeit-Management: Protokollier Ankunfts- und Abgangszeiten präzise.
3. Status-Logik: Entscheidet, ob ein Objekt neu ist, zurückgekehrt ist oder den Bereich verlassen hat.

Design-Notizen
--------------
- Entkopplung: Der Tracking-Loop (Vision) muss nicht wissen, wie die Datenbank funktioniert. Er ruft nur diese API auf.
- Konsistenz: Verwendet eine zentrale Helper-Funktion für Zeitstempel, um das Format (YYYY-MM-DD HH:MM:SS) überall gleich zu halten.
- Sicherheit: Prüft vor jedem Schreibvorgang den aktuellen Datenbank-Status, um Überschreibungen zu vermeiden.
"""

from database import DatabaseManager
from datetime import datetime

def _get_current_timestamp():
    """Helper-Funktion für einen sauberen, einheitlichen Zeitstempel-String."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def schrank_gesehen(schrank_id):
    """
    Wird vom Kamerasystem aufgerufen, wenn ein QR-Code (wieder) erkannt wird.
    
    Logik:
    1. Wenn 'erscheinungspunkt' leer ist: Setze ihn (Erster Scan / Registrierung).
    2. Wenn 'abgangspunkt' gesetzt ist: Leere ihn (Der Schrank ist zurückgekehrt/Wiederaufnahme).
    """
    print(f"[Tracking API] GESEHEN: ID {schrank_id}")
    db = DatabaseManager()
    
    # 1. Aktuellen Status aus der Datenbank holen
    current_data = db.get_schrank_by_id(schrank_id)
    if not current_data:
        print(f"[Tracking API] FEHLER: ID {schrank_id} nicht in DB gefunden.")
        return

    # 2. Status ermitteln
    is_erster_scan = (current_data['erscheinungspunkt'] is None)
    ist_zurueckgekehrt = (current_data['abgangspunkt'] is not None)

    # 3. Fallunterscheidung und Updates
    
    # Fall A: Der Schrank wird zum allerersten Mal gesehen
    if is_erster_scan:
        timestamp = _get_current_timestamp()
        db.update_erscheinungszeit(schrank_id, timestamp)
        print(f"[Tracking API] ID {schrank_id} zum ERSTEN Mal erfasst um {timestamp}.")

    # Fall B: Der Schrank war weg (hatte Abgangszeit) und ist jetzt wieder da
    if ist_zurueckgekehrt:
        # Wir löschen die Abgangszeit, da er wieder anwesend ist
        db.update_abgangszeit(schrank_id, None)
        print(f"[Tracking API] ID {schrank_id} ist ZURÜCKgekehrt. Abgangszeit gelöscht.")
        
    # Info: Wenn beides nicht zutrifft, ist der Schrank einfach weiterhin da
    if not is_erster_scan and not ist_zurueckgekehrt:
        pass # print(f"[Tracking API] ID {schrank_id} ist bereits als anwesend markiert.")

def schrank_verloren(schrank_id):
    """
    Wird vom Kamerasystem aufgerufen, wenn ein QR-Code nicht mehr gesehen wird
    (nach Ablauf der Toleranzzeit oder Kill-Zone).
    
    Logik:
    1. Trägt die Abgangszeit ein, ABER nur, wenn sie noch leer ist.
       So wird verhindert, dass der erste Zeitstempel des Verschwindens überschrieben wird.
    """
    print(f"[Tracking API] VERLOREN: ID {schrank_id}")
    db = DatabaseManager()

    # 1. Aktuellen Status holen
    current_data = db.get_schrank_by_id(schrank_id)
    if not current_data:
        print(f"[Tracking API] FEHLER: ID {schrank_id} nicht in DB gefunden.")
        return

    # 2. Nur eintragen, wenn er nicht bereits als "verloren" markiert ist
    if current_data['abgangspunkt'] is None:
        timestamp = _get_current_timestamp()
        db.update_abgangszeit(schrank_id, timestamp)
        print(f"[Tracking API] ID {schrank_id} als ABGEGANGEN markiert um {timestamp}.")
    else:
        # Sollte im Normalbetrieb selten vorkommen, da der Manager das filtert
        print(f"[Tracking API] ID {schrank_id} ist bereits als abwesend markiert.")
