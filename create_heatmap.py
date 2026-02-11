import cv2
import numpy as np
from database import DatabaseManager
import config
import os

def generate_heatmap():
    print("--- Generiere Heatmap aus DB-Daten ---")
    
    # 1. Map laden
    try:
        map_img = cv2.imread(config.MAP_FILE)
    except:
        map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grundriss.png")
        map_img = cv2.imread(map_path)
        
    if map_img is None:
        print("Grundriss nicht gefunden.")
        return

    height, width = map_img.shape[:2]

    # 2. Daten holen
    db = DatabaseManager()
    points = db.get_all_movements()
    print(f"{len(points)} Datenpunkte gefunden.")

    if not points:
        print("Keine Daten vorhanden. Lass das Tracking erst eine Weile laufen!")
        return

    # 3. Leere Maske (Accumulator) erstellen
    # Wir nutzen Float, damit wir addieren können ohne Überlauf
    heatmap_mask = np.zeros((height, width), dtype=np.float32)

    # 4. Punkte einzeichnen
    # Je mehr Punkte an einer Stelle, desto "heißer"
    for row in points:
        x, y = row['x'], row['y']
        
        # Sicherstellen, dass x/y im Bild sind
        if 0 <= x < width and 0 <= y < height:
            # Wir malen einen unscharfen "Klecks" an die Stelle
            # Radius = 30px, Intensität = 1
            # Man kann hier auch cv2.circle benutzen und danach erst blurren
            
            # Einfachste Methode: Kleiner weißer Kreis
            temp_layer = np.zeros((height, width), dtype=np.float32)
            cv2.circle(temp_layer, (x, y), 25, (1.0), -1) 
            
            # Auf die Heatmap addieren
            heatmap_mask += temp_layer

    # 5. Normalisieren (0 bis 255)
    # Damit der heißeste Punkt 255 ist
    if np.max(heatmap_mask) > 0:
        heatmap_mask = heatmap_mask / np.max(heatmap_mask) * 255
    
    heatmap_mask = np.uint8(heatmap_mask)

    # 6. Einfärben (False Color)
    # COLORMAP_JET macht: Blau (kalt) -> Grün -> Rot (heiß)
    heatmap_color = cv2.applyColorMap(heatmap_mask, cv2.COLORMAP_JET)

    # 7. Überlagern mit dem Grundriss
    # alpha = 0.6 (Map), beta = 0.4 (Heatmap)
    final_result = cv2.addWeighted(map_img, 0.6, heatmap_color, 0.4, 0)

    # Anzeigen
    cv2.imshow("Heatmap Analyse", final_result)
    print("Drücke eine Taste zum Beenden und Speichern.")
    cv2.waitKey(0)
    
    cv2.imwrite("heatmap_result.png", final_result)
    print("Gespeichert als heatmap_result.png")
    cv2.destroyAllWindows()

if __name__ == "__main__":
    generate_heatmap()
