# schrank.py
"""
Datenmodell / Entity-Klasse.

Zweck
-----
Diese Datei definiert die Struktur eines 'Schrank'-Objekts im Speicher.
Sie dient als Datentransferobjekt (DTO), um Informationen strukturiert zwischen
der Datenbank-Schicht und der Anwendungslogik zu übergeben.

Design-Notizen
--------------
- Leichtgewichtig: Enthält nur Datenfelder, keine komplexe Geschäftslogik.
- Debugging-freundlich: Die `__repr__`-Methode sorgt dafür, dass Listen von Schränken
  in der Konsole lesbar ausgegeben werden, statt nur Speicheradressen anzuzeigen.
"""

class Schrank:
    """
    Eine einfache Klasse, die einen Schrank (Inventar-Objekt) repräsentiert.
    Spiegelt im Wesentlichen eine Zeile der Datenbank-Tabelle 'schraenke' wider.
    """
    
    def __init__(self, ware, erscheinungspunkt, abgangspunkt):
        """
        Initialisiert ein neues Schrank-Objekt.

        Argumente:
        - ware: Beschreibung des Inhalts (String).
        - erscheinungspunkt: Zeitstempel des ersten Erkennens (Startzeit).
        - abgangspunkt: Zeitstempel des Verschwindens (Endzeit, kann None sein).
        """
        self.ware = ware
        self.erscheinungspunkt = erscheinungspunkt
        self.abgangspunkt = abgangspunkt

    def __repr__(self):
        """
        Liefert eine formale String-Repräsentation des Objekts.
        Nützlich für Debugging (z.B. print(list_of_schraenke)).
        """
        return f"<Schrank(ware='{self.ware}', von='{self.erscheinungspunkt}')>"
