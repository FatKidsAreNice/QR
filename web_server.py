from flask import Flask, abort
from database import DatabaseManager

app = Flask(__name__)

# WICHTIG: Keine eigene DB_FILE Konstante definieren, die falsch ist.
# Wir verlassen uns auf den Default in DatabaseManager.

@app.route('/')
def index():
    return "Willkommen beim Schrank-Inventar-System. Scanne einen QR-Code."

@app.route('/schrank/<int:schrank_id>')
def get_schrank_details(schrank_id):
    print(f"Anfrage für Schrank ID {schrank_id} empfangen...")
    
    try:
        # Hier KEIN Argument übergeben, damit er 'Schrank_Bestand.db' nimmt
        db_manager = DatabaseManager()
        schrank_data = db_manager.get_schrank_by_id(schrank_id)
        
        if schrank_data:
            ware_val = schrank_data['ware']
            # Sicherstellen, dass None als Striche angezeigt wird
            erschien_val = schrank_data['erscheinungspunkt'] or "---"
            abgang_val = schrank_data['abgangspunkt'] or "---"

            html_output = f"""
            <html>
            <head>
                <title>Schrank Details</title>
                <meta http-equiv="refresh" content="5"> <style>
                    body {{ font-family: sans-serif; padding: 20px; }}
                    .container {{ border: 1px solid #ccc; padding: 20px; max-width: 600px; }}
                </style>
            </head>
            <body>
                <div class='container'>
                    <h1>Schrank ID: {schrank_data['id']}</h1>
                    <p><strong>Ware:</strong> {ware_val}</p>
                    <p><strong>Erstes Erscheinen:</strong> {erschien_val}</p>
                    <p><strong>Letzter Abgang:</strong> {abgang_val}</p>
                </div>
            </body>
            </html>
            """
            return html_output
        else:
            print(f"Schrank ID {schrank_id} nicht gefunden.")
            abort(404, description="Schrank nicht gefunden")
            
    except Exception as e:
        print(f"Server-Fehler: {e}")
        abort(500, description="Interner Serverfehler")

def start_server():
    print("Starte den Web-Server auf http://127.0.0.1:5000 ...")
    app.run(debug=True, port=5000, use_reloader=False, host='0.0.0.0')

if __name__ == "__main__":
    start_server()
