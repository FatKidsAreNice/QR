# Track&TrAIce 🥓🔍

**KI-basierte Bestandsüberwachung und Lokalisierung von Warenträgern in der Lebensmittelindustrie.**

> **Interdisziplinäres Projekt (WiSe 25/26)** > **Praxispartner:** Sauels AG (Kempen)

## 📖 Über das Projekt
Track&TrAIce ist ein **Proof-of-Concept (PoC)** zur Lösung eines spezifischen Logistikproblems in Kühlhäusern. Aufgrund von extremen Temperaturen in den Öfen (Backprozess) können Wurstschränke nicht mit aktiver Elektronik (RFID/Bluetooth) ausgestattet werden. 

Unsere Lösung nutzt **Computer Vision**, um Warenträger kontaktlos zu identifizieren und im Lager zu lokalisieren.

### Kernfunktionen
* **Hybrides Tracking:** Kombination aus Objekterkennung (**YOLOv8**) zur Lokalisierung und Algorithmus-basiertem **QR-Code-Scanning** zur Identifikation.
* **Echtzeit-Mapping:** Projektion der physischen Positionen auf einen digitalen Lager-Grundriss (Visualisierung).
* **Datenbank-Integration:** Automatische Erfassung von Verweilzeiten und Zeitstempeln (SQLite) zur Einhaltung der Kühlkette.
* **Hardware:** Entwickelt auf **NVIDIA Jetson Nano** mit Arducam (Vogelperspektive).

---

## 🛠️ Technologie-Stack
* **Sprache:** Python 3.x
* **KI/Vision:** Ultralytics YOLOv8, OpenCV
* **Datenbank:** SQLite
* **Hardware:** NVIDIA Jetson Nano, Arducam IMX519

## ⚠️ Hardware-Hinweis
Dieses Repository enthält den Quellcode für die spezifische Laborumgebung des Projekts. Da die Software eng an die Hardware-Konfiguration (Kameramontage an der Decke, spezifische Objektive, Jetson-GPIOs) gekoppelt ist, dient dieser Code primär der **Dokumentation und Einsicht**. Ein 1:1 Nachbau ohne die entsprechende physische Konstruktion ist nicht ohne Anpassungen möglich.

## 🚀 Installation & Ausführung

### Voraussetzungen
* Python 3.8+
* Installierte Bibliotheken gemäß `requirements.txt`

### Setup
1.  Repository klonen:
    ```bash
    git clone [https://github.com/alex-basalo/Track-TrAIce.git](https://github.com/alex-basalo/Track-TrAIce.git)
    cd Track-TrAIce
    ```

2.  Abhängigkeiten installieren:
    ```bash
    pip install -r requirements.txt
    ```

### Starten der Anwendung
Das Hauptskript befindet sich im `src`-Ordner. Da für den Zugriff auf die Kamera-Hardware (auf dem Jetson Nano) und ggf. GPIOs administrative Rechte nötig sein können, wird das Skript mit `sudo` ausgeführt:

```bash
sudo python3 src/Tracking_main.py
```
Das System initialisiert daraufhin den Kamerastream, lädt das YOLO-Modell und startet die Datenbank-Verbindung.

---

## 📂 Struktur
* `src/`: Enthält den gesamten Source Code (Main-Logik, Tracking-Skripte, DB-Handler).
* `requirements.txt`: Liste der Python-Abhängigkeiten.
* `README.md`: Projektdokumentation.

---

## 👥 Das Team
* Leon Julke
* Lukas Kennerknecht
* Alexander Basalo
* Leonard Hermanns

*Hochschule Niederrhein – Faculty of Industrial Engineering*
