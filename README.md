# PHK 180 Local Web Control (Unofficial Home Assistant Integration)

[![Home Assistant Marketplace](https://img.shields.io/badge/Home%20Assistant-Marketplace%20(Custom)-41BDF5.svg)](https://www.home-assistant.io/integrations/marketplace/)

> **RECHTLICHER HINWEIS / DISCLAIMER (KEIN HERSTELLERPROJEKT):**
> Dies ist ein **unabhängiges, privates und inoffizielles Open-Source-Community-Projekt** (`phk180`) unter der **MIT-Lizenz**.
> Dieses Projekt steht in **keinerlei wirtschaftlicher, organisatorischer oder rechtlicher Verbindung** zur *AEREX HaustechnikSysteme GmbH* oder der *MAICO-Gruppe* und wird von diesen weder autorisiert, geprüft, gesponsert noch unterstützt.
> Sämtliche Marken- und Modellbezeichnungen (insbesondere *AEREX*, *PHK 180* und *PHS 300*) sind Eigentum ihrer jeweiligen Rechtsinhaber und werden in diesem Repository ausschließlich zur sachlichen Beschreibung der technischen Interoperabilität (Kompatibilitätshinweis gemäß § 23 MarkenG) verwendet.
> Die Nutzung dieser Software erfolgt auf eigene Gefahr. Sicherheitsrelevante Einrichtungen der Anlage (wie Türkontaktschalter, Sicherheitstemperaturbegrenzer oder Druckwächter) dürfen niemals verändert oder überbrückt werden.

---

## Überblick
Diese Integration ermöglicht die lokale Einbindung einer **PHK 180** Lüftungs- und Wärmepumpenanlage (mit **PHS 300** Trinkwasserspeicher) in Home Assistant über die im lokalen Netzwerk erreichbare HTTP/XML-Weboberfläche (`.cgx` / `.htm`) der Endkunden-Ebene.

### Hauptmerkmale
- **100 % Lokal (Local Polling):** Direkte Kommunikation im Heimnetzwerk ohne Cloud-Abhängigkeit.
- **Nur Endkunden-Ebene:** Die Integration greift ausschließlich auf Einstellungen und Abfragewerte zu, die auf der regulären Endkunden-Weboberfläche vorgesehen sind. Passwortgeschützte Installateur- oder Service-Ebenen werden weder abgefragt noch freigeschaltet.
- **Closed-Loop Sollwertregelung mit technischer Grenzwertprüfung:** Alle einstellbaren Temperatur-, Hysterese- und Lüftungsparameter sind auf ihre technisch zulässigen Betriebsgrenzen begrenzt, sodass unzulässige Sollwerte gar nicht erst an das Gerät gesendet werden.
- **Direktsteuerung:** Betriebsart, Lüftungsstufe, Stoßlüftung, Jahreszeit, Legionellenschutz, Vorrangschaltung sowie Ferienbetrieb.
- **Über 50 Entitäten:** Alle Temperaturen, Lüfterdrehzahlen, Volumenströme, CO2-Werte, Schaltzustände und alle 14 Betriebsstundenzähler.

---

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=AcOscar&repository=ha-phk180&category=integration)

### Variante A: Über Marketplace (Empfohlen)
1. Öffne in Home Assistant **Marketplace -> Drei-Punkte-Menü (oben rechts) -> Benutzerdefinierte Repositories**.
2. Trage die URL dieses GitHub-Repositories (`https://github.com/AcOscar/ha-phk180`) ein und wähle als Typ **Integration**.
3. Suche nach **PHK 180 Local Web Control (Unofficial)**, klicke auf **Herunterladen** und starte Home Assistant neu.
4. Gehe auf **Einstellungen -> Geräte & Dienste -> Integration hinzufügen** und suche nach **PHK 180 Local Web Control**.

### Variante B: Manuelle Installation
1. Kopiere den Ordner `custom_components/phk180` in dein Home Assistant Verzeichnis unter `/config/custom_components/phk180`.
2. *(Optional für das Live-Schema)* Kopiere den Ordner `www/phk180` nach `/config/www/phk180`.
3. Starte Home Assistant neu und füge die Integration unter **Einstellungen -> Geräte & Dienste** hinzu.

## Lizenz
Veröffentlicht unter der [MIT License](LICENSE).
