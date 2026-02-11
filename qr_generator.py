# qr_generator.py
import qrcode
import os

class QRCodeGenerator:
    # ... (__init__ bleibt gleich) ...
    def __init__(self, output_dir="qr_codes", base_url="http://127.0.0.1:5000/schrank/"):
        self.output_dir = output_dir
        self.base_url = base_url
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    # ... (create_qr_for_schrank bleibt gleich) ...
    def create_qr_for_schrank(self, schrank_id):
        url = f"{self.base_url}{schrank_id}"
        try:
            filename = f"schrank_{schrank_id}.png"
            filepath = os.path.join(self.output_dir, filename)
            img = qrcode.make(url)
            img.save(filepath)
            # (Wir entfernen das 'print' auch von hier)
            return filepath
        except Exception as e:
            print(f"Fehler beim Erstellen des QR-Codes für ID {schrank_id}: {e}")
            return None

    # --- NEUE FUNKTION ---
    def delete_qr_for_schrank(self, schrank_id):
        """
        Löscht die QR-Code-Bilddatei, die zu einer Schrank-ID gehört.
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
            # OSError fängt Fehler ab, z.B. wenn die Datei gesperrt ist
            print(f"Fehler beim Löschen der QR-Code-Datei: {e}")