# qr_generator.py
"""
QR-Code Management / Generator.

Zweck
-----
Diese Klasse verbindet die physische Welt mit der digitalen Datenbank:
1. Generierung: Erstellt QR-Codes, die eine URL zur spezifischen Schrank-ID enthalten.
2. Dateisystem-Verwaltung: Speichert die generierten Bilder in einem definierten Ordner.
3. Bereinigung: Löscht QR-Codes, wenn zugehörige Schränke aus der Datenbank entfernt werden (Garbage Collection).

Design-Notizen
--------------
- Robustheit: Prüft vor dem Speichern/Löschen, ob Verzeichnisse oder Dateien existieren.
- Fehlerbehandlung: Fängt Dateisystem-Fehler (OSError) ab, um Programmabstürze zu vermeiden, wenn Dateien blockiert sind.
- Flexibilität: Die Base-URL ist konfigurierbar, um auf verschiedene Server-Adressen (Localhost/Produktion) zu zeigen.
"""

import qrcode
import os

class QRCodeGenerator:
    def __init__(self, output_dir="qr_codes", base_url="http://127.0.0.1:5000/schrank/"):
        """
        Initialisiert den Generator und stellt sicher, dass der Ausgabeordner existiert.
        """
        self.output_dir = output_dir
        self.base_url = base_url
        
        # Sicherstellen, dass das Verzeichnis existiert
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    # ---------- Erstellung ----------

    def create_qr_for_schrank(self, schrank_id):
        """
        Generiert einen QR-Code für eine gegebene Schrank-ID.
        
        Der QR-Code enthält eine URL (z.B. .../schrank/12), die beim Scannen
        direkt zur Detailansicht des Objekts führt.
        """
        url = f"{self.base_url}{schrank_id}"
        try:
            # Dateipfad konstruieren
            filename = f"schrank_{schrank_id}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            # QR-Code erzeugen und speichern
            img = qrcode.make(url)
            img.save(filepath)
            
            return filepath
        except Exception as e:
            print(f"Fehler beim Erstellen des QR-Codes für ID {schrank_id}: {e}")
            return None

    # ---------- Bereinigung ----------

    def delete_qr_for_schrank(self, schrank_id):
        """
        Löscht die physische Bilddatei, die zu einer Schrank-ID gehört.
        Wird aufgerufen, wenn ein Eintrag aus der Datenbank entfernt wird.
        """
        try:
            filename = f"schrank_{schrank_id}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            # Prüfen, ob die Datei existiert, bevor wir sie löschen
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"QR-Code-Datei {filepath} gelöscht.")
            else:
                print(f"QR-Code-Datei für ID {schrank_id} nicht gefunden, nichts zu löschen.")
        
        except OSError as e:
            # OSError fängt Fehler ab, z.B. wenn die Datei gerade geöffnet/gesperrt ist
            print(f"Fehler beim Löschen der QR-Code-Datei: {e}")
