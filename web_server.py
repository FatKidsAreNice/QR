# server.py
"""
Web-Server / Informations-Interface.

Zweck
-----
Diese Datei stellt den Web-Zugriffspunkt für das System bereit:
1. QR-Code-Ziel: Wenn ein QR-Code gescannt wird (z.B. mit dem Handy), führt der Link hierher.
2. Status-Anzeige: Liest die aktuellen Daten aus der Datenbank und zeigt sie als HTML an.
3. Live-Monitoring: Die Webseite aktualisiert sich automatisch (Auto-Refresh), um Statusänderungen (da/weg) anzuzeigen.

Design-Notizen
--------------
- Micro-Framework: Nutzt Flask für einen leichtgewichtigen HTTP-Server.
- Server-Side Rendering: Generiert einfaches HTML direkt im Code (keine externen Templates nötig).
- Netzwerk-Sichtbarkeit: Läuft auf '0.0.0.0', damit der Server auch von anderen Geräten im WLAN (z.B. Handy) erreichbar ist.
- Fehlerbehandlung: Fängt nicht vorhandene IDs (404) und Datenbank-Fehler (500) sauber ab.
"""

from flask import Flask, abort
from database import DatabaseManager

app = Flask(__name__)

# WICHTIG: Keine eigene DB_FILE Konstante definieren, die falsch ist.
# Wir verlassen uns auf den Default in DatabaseManager, um Konsistenz zu wahren.

@app.route('/')
def index():
    """Startseite / Landing Page."""
    return "Willkommen beim Schrank-Inventar-System. Scanne einen QR-Code."

@app.route('/schrank/<int:schrank_id>')
def get_schrank_details(schrank_id):
    """
    Detail-Ansicht für einen spezifischen Schrank.
    
    Argumente:
    - schrank_id: Wird aus der URL extrahiert (z.B. /schrank/12 -> ID=12).
    """
    print(f"Anfrage für Schrank ID {schrank_id} empfangen...")
    
    try:
        # ---------- 1. Datenbeschaffung ----------
        # Hier KEIN Argument übergeben, damit er automatisch 'Schrank_Bestand.db' nimmt
        db_manager = DatabaseManager()
        schrank_data = db_manager.get_schrank_by_id(schrank_id)
        
        # ---------- 2. HTML-Generierung ----------
        if schrank_data:
            # Daten für die Anzeige aufbereiten
            ware_val = schrank_data['ware']
            # Sicherstellen, dass None (Leere Werte) als Striche "---" angezeigt wird
            erschien_val = schrank_data['erscheinungspunkt'] or "---"
            abgang_val = schrank_data['abgangspunkt'] or "---"

            # Einfaches HTML-Template mit eingebetteten CSS-Styles
            # Der meta-refresh sorgt dafür, dass sich die Seite alle 5 Sekunden neu lädt
            html_output = f"""
            <html>
            <head>
                <title>Schrank Details</title>
                <meta http-equiv="refresh" content="5"> 
                <style>
                    body {{ font-family: sans-serif; padding: 20px; background-color: #f4f4f4; }}
                    .container {{ 
                        border: 1px solid #ccc; 
                        padding: 20px; 
                        max-width: 600px; 
                        background-color: white; 
                        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
                        margin: 0 auto;
                    }}
                    h1 {{ color: #333; }}
                    p {{ font-size: 1.1em; line-height: 1.5; }}
                </style>
            </head>
            <body>
                <div class='container'>
                    <h1>Schrank ID: {schrank_data['id']}</h1>
                    <hr>
                    <p><strong>Ware:</strong> {ware_val}</p>
                    <p><strong>Erstes Erscheinen:</strong> {erschien_val}</p>
                    <p><strong>Letzter Abgang:</strong> {abgang_val}</p>
                </div>
            </body>
            </html>
            """
            return html_output
        else:
            # Fall: ID existiert nicht in der Datenbank
            print(f"Schrank ID {schrank_id} nicht gefunden.")
            abort(404, description="Schrank nicht gefunden")
            
    except Exception as e:
        print(f"Server-Fehler: {e}")
        abort(500, description="Interner Serverfehler")

def start_server():
    """
    Startet den Flask-Server.
    
    Parameter:
    - host='0.0.0.0': Erlaubt Zugriff von außen (z.B. Handy im gleichen WLAN).
    - use_reloader=False: Verhindert doppelte Ausführung bei manchen IDEs/Setups.
    """
    print("Starte den Web-Server auf http://127.0.0.1:5000 ...")
    app.run(debug=True, port=5000, use_reloader=False, host='0.0.0.0')

if __name__ == "__main__":
    start_server()
