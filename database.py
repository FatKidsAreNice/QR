# database.py
"""
Datenbank-Schnittstelle / Persistenz-Layer.

Zweck
-----
Diese Datei verwaltet die dauerhafte Speicherung aller Daten (SQLite):
1. Inventar-Verwaltung: Speichert Schränke/Objekte mit Status (Ware) und Zeitstempeln (Erscheinung/Abgang).
2. Bewegungs-Tracking: Loggt X/Y-Koordinaten für spätere Analysen (z.B. Heatmap).
3. Ressourcen-Management: Sicheres Öffnen/Schließen der Verbindung via Context Manager.

Design-Notizen
--------------
- Context Manager: Implementiert `__enter__` und `__exit__`, um Verbindungen automatisch zu schließen.
- Row Factory: Nutzt `sqlite3.Row`, damit Datenbank-Ergebnisse wie Dictionaries (Zugriff per Spaltenname) behandelt werden können.
- Fehlerbehandlung: Kritische Operationen sind in Try-Except-Blöcken gekapselt.
"""

import sqlite3
from datetime import datetime

# Name der Datenbank-Datei als Konstante
DB_FILE = 'Schrank_Bestand.db'

class DatabaseManager:
    def __init__(self, db_file=DB_FILE):
        """Konstruktor: Setzt den Dateipfad, öffnet aber noch keine Verbindung."""
        self.db_file = db_file
        self.conn = None

    def __enter__(self):
        """
        Ermöglicht die Nutzung des 'with'-Statements.
        Öffnet die Verbindung und setzt die Row-Factory.
        """
        try:
            self.conn = sqlite3.connect(self.db_file)
            self.conn.row_factory = sqlite3.Row 
            return self
        except sqlite3.Error as e:
            print(f"Fehler beim Verbinden mit der Datenbank: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Wird am Ende des 'with'-Blocks aufgerufen.
        Schließt die Verbindung sauber.
        """
        if self.conn:
            self.conn.close()

    # ---------- Tabellen-Initialisierung ----------

    def create_schrank_table(self):
        """Erstellt die Haupttabelle 'schraenke', falls sie nicht existiert."""
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

    # ---------- CRUD Operationen (Inventar) ----------

    def insert_schrank(self, schrank_instance):
        """Fügt einen neuen Schrank-Eintrag hinzu und gibt die neue ID zurück."""
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
                return new_id
        except sqlite3.Error as e:
            print(f"Fehler beim Einfügen des Schrankes: {e}")
            self.conn.rollback()
            return None

    def get_schrank_by_id(self, schrank_id):
        """Liest einen Schrank anhand der ID aus und gibt ihn als Dictionary zurück."""
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

    def delete_schrank_by_id(self, schrank_id):
        """
        Löscht einen einzelnen Schrank anhand seiner ID aus der Datenbank.
        Rückgabe: True bei Erfolg, False wenn ID nicht gefunden oder Fehler.
        """
        sql = "DELETE FROM schraenke WHERE id = ?;"
        try:
            with self:
                cursor = self.conn.cursor()
                cursor.execute(sql, (schrank_id,))
                self.conn.commit()
                
                # Prüfen, ob eine Zeile betroffen war
                if cursor.rowcount > 0:
                    return True
                else:
                    return False
        except sqlite3.Error as e:
            print(f"Fehler beim Löschen von ID {schrank_id}: {e}")
            return False
    
    # ---------- Zeit-Management & Status-Logik ----------

    def update_erscheinungszeit(self, schrank_id, timestamp):
        """Setzt explizit den 'erscheinungspunkt' (Zeit) für eine ID."""
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
        """Setzt explizit den 'abgangspunkt'. Timestamp=None leert das Feld."""
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
        """
        Komplexe Status-Logik für Anwesenheit (Active/Inactive).
        
        Logik:
        - Inactive (Abgang): Setzt Abgangszeit, löscht Erscheinungszeit.
        - Active (Eingang/Rückkehr): Löscht Abgangszeit, setzt neue Erscheinungszeit (falls leer).
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                if status == "inactive":
                    # --- ABGANG ---
                    # Setzt Abgangszeit und entfernt den alten Startpunkt
                    cursor.execute("""
                        UPDATE schraenke 
                        SET abgangspunkt = ?, erscheinungspunkt = NULL 
                        WHERE id = ?
                    """, (timestamp, uid))
                    
                elif status == "active":
                    # --- EINGANG ---
                    # Schritt A: Abgang entfernen (da Objekt wieder da ist)
                    cursor.execute("""
                        UPDATE schraenke 
                        SET abgangspunkt = NULL 
                        WHERE id = ?
                    """, (uid,))
                    
                    # Schritt B: Neue Startzeit setzen, falls Feld leer ist
                    cursor.execute("""
                        UPDATE schraenke 
                        SET erscheinungspunkt = ? 
                        WHERE id = ? AND erscheinungspunkt IS NULL
                    """, (timestamp, uid))
                    
                conn.commit()
                print(f"[DB] ID {uid} Status '{status}' -> Zeiten aktualisiert.")
                
        except Exception as e:
            print(f"DB Fehler bei Update ID {uid}: {e}")
            
    # ---------- Bewegungs-Log (Analytics) ----------

    def create_movement_table(self):
        """Erstellt die Tabelle 'movement_log' für die Historie der Positionen."""
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
        """
        Speichert einen Positions-Schnappschuss mit aktuellem Zeitstempel.
        Dient zur Erstellung von Bewegungspfaden oder Heatmaps.
        """
        try:
            # Timestamp hier generieren, da 'datetime' importiert ist
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
        """Holt alle rohen X/Y-Koordinaten für die Visualisierung."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT x, y FROM movement_log")
                return cursor.fetchall()
        except Exception as e:
            print(f"Fetch Error: {e}")
            return []
