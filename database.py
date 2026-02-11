# database.py
import sqlite3

# Name der Datenbank-Datei als Konstante
DB_FILE = 'Schrank_Bestand.db'

class DatabaseManager:
    # ... (__init__, __enter__, __exit__, create_schrank_table bleiben gleich) ...
    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        self.conn = None

    def __enter__(self):
        try:
            self.conn = sqlite3.connect(self.db_file)
            self.conn.row_factory = sqlite3.Row 
            return self
        except sqlite3.Error as e:
            print(f"Fehler beim Verbinden mit der Datenbank: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def create_schrank_table(self):
        with self:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schraenke (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ware TEXT NOT NULL,
                        erscheinungspunkt TEXT,
                        abgangspunkt TEXT
                    );
                """)
                self.conn.commit()
                print("Tabelle 'schraenke' erfolgreich sichergestellt.")
            except sqlite3.Error as e:
                print(f"Fehler beim Erstellen der Tabelle: {e}")
    
    # ... (insert_schrank bleibt gleich) ...
    def insert_schrank(self, schrank_instance):
        sql = """
            INSERT INTO schraenke (ware, erscheinungspunkt, abgangspunkt) 
            VALUES (?, ?, ?);
        """
        try:
            with self:
                cursor = self.conn.cursor()
                data_tuple = (
                    schrank_instance.ware, 
                    schrank_instance.erscheinungspunkt, 
                    schrank_instance.abgangspunkt
                )
                cursor.execute(sql, data_tuple)
                self.conn.commit()
                new_id = cursor.lastrowid
                # (Wir entfernen das 'print' von hier, 
                # damit das Skript 'add_schrank.py' die Kontrolle hat)
                return new_id
        except sqlite3.Error as e:
            print(f"Fehler beim Einfügen des Schrankes: {e}")
            self.conn.rollback()
            return None

    # ... (get_schrank_by_id bleibt gleich) ...
    def get_schrank_by_id(self, schrank_id):
        sql = "SELECT * FROM schraenke WHERE id = ?;"
        try:
            with self:
                cursor = self.conn.cursor()
                cursor.execute(sql, (schrank_id,))
                result = cursor.fetchone() 
                if result:
                    return dict(result) 
                else:
                    return None
        except sqlite3.Error as e:
            print(f"Fehler beim Abrufen von Schrank {schrank_id}: {e}")
            return None

    # --- NEUE FUNKTION ---
    def delete_schrank_by_id(self, schrank_id):
        """
        Löscht einen einzelnen Schrank anhand seiner ID aus der Datenbank.
        Gibt True zurück, wenn erfolgreich, sonst False.
        """
        sql = "DELETE FROM schraenke WHERE id = ?;"
        try:
            with self:
                cursor = self.conn.cursor()
                cursor.execute(sql, (schrank_id,))
                self.conn.commit()
                
                # cursor.rowcount gibt an, wie viele Zeilen betroffen waren.
                # Wenn es 1 ist, war der Löschvorgang erfolgreich.
                if cursor.rowcount > 0:
                    return True
                else:
                    # ID wurde nicht gefunden, aber kein Fehler
                    return False
        except sqlite3.Error as e:
            print(f"Fehler beim Löschen von ID {schrank_id}: {e}")
            return False
    
    def update_erscheinungszeit(self, schrank_id, timestamp):
        """
        Setzt den 'erscheinungspunkt' (Zeit) für eine bestimmte ID.
        """
        sql = "UPDATE schraenke SET erscheinungspunkt = ? WHERE id = ?;"
        try:
            with self:
                cursor = self.conn.cursor()
                cursor.execute(sql, (timestamp, schrank_id))
                self.conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Fehler beim Update der Erscheinungszeit für ID {schrank_id}: {e}")
            return False

    def update_abgangszeit(self, schrank_id, timestamp):
        """
        Setzt den 'abgangspunkt' (Zeit) für eine bestimmte ID.
        Wenn timestamp=None ist, wird das Feld geleert (z.B. bei Rückkehr).
        """
        sql = "UPDATE schraenke SET abgangspunkt = ? WHERE id = ?;"
        try:
            with self:
                cursor = self.conn.cursor()
                cursor.execute(sql, (timestamp, schrank_id))
                self.conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Fehler beim Update der Abgangszeit für ID {schrank_id}: {e}")
            return False
            
    def update_schrank_status(self, uid, status, timestamp):
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                if status == "inactive":
                    # --- ABGANG ---
                    # 1. Abgangszeit setzen (timestamp)
                    # 2. Erscheinungspunkt LÖSCHEN (NULL), wie von dir gewünscht.
                    #    Damit ist der alte "Start" vom 7.1. weg.
                    cursor.execute("""
                        UPDATE schraenke 
                        SET abgangspunkt = ?, erscheinungspunkt = NULL 
                        WHERE id = ?
                    """, (timestamp, uid))
                    
                elif status == "active":
                    # --- EINGANG ---
                    # 1. Abgangszeit löschen (er ist ja wieder da)
                    # 2. Erscheinungszeit setzen (aber nur, wenn sie leer/NULL ist)
                    #    Da wir sie beim Abgang gelöscht haben, wird sie hier frisch auf "Jetzt" gesetzt.
                    
                    # Schritt A: Abgang entfernen
                    cursor.execute("""
                        UPDATE schraenke 
                        SET abgangspunkt = NULL 
                        WHERE id = ?
                    """, (uid,))
                    
                    # Schritt B: Startzeit schreiben (nur wenn Feld leer ist)
                    cursor.execute("""
                        UPDATE schraenke 
                        SET erscheinungspunkt = ? 
                        WHERE id = ? AND erscheinungspunkt IS NULL
                    """, (timestamp, uid))
                    
                conn.commit()
                # Debug-Ausgabe
                print(f"[DB] ID {uid} Status '{status}' -> Zeiten aktualisiert.")
                
        except Exception as e:
            print(f"DB Fehler bei Update ID {uid}: {e}")
            
    # In DatabaseManager Klasse einfügen:

    def create_movement_table(self):
        """Erstellt Tabelle für Bewegungshistorie."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS movement_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        schrank_id INTEGER,
                        x INTEGER,
                        y INTEGER,
                        timestamp TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"Fehler beim Erstellen der Log-Tabelle: {e}")

    def log_movement(self, schrank_id, x, y):
        """Speichert eine Position mit Zeitstempel."""
        try:
            from datetime import datetime
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO movement_log (schrank_id, x, y, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (schrank_id, int(x), int(y), now))
                conn.commit()
        except Exception as e:
            print(f"Log Error: {e}")
            
    def get_all_movements(self):
        """Holt alle Bewegungsdaten für die Heatmap."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT x, y FROM movement_log")
                return cursor.fetchall()
        except Exception as e:
            print(f"Fetch Error: {e}")
            return []
