# Weishaupt WTC-OB über eBUS in Home Assistant

**Weishaupt-Ölbrennwertkessel WTC-OB mit WCM-FS direkt am eBUS auslesen und einstellen: mit einem eBUS-Adapter, ebusd und Home Assistant, ohne WCM-COM.**

Dieses Projekt ersetzt das Weishaupt-Kommunikationsmodul **WCM-COM** (und seine langsame Weboberfläche) durch einen günstigen eBUS-Adapter. Die herstellerspezifischen Weishaupt-Telegramme sind hier dokumentiert, einschließlich des Prüfbytes, das bisher den Nachbau verhindert hat. Dazu gibt es fertige Dateien für ebusd und Home Assistant.

> 🇬🇧 **English summary** at the [bottom of this page](#english-summary).

---

## Was du bekommst

| | |
|---|---|
| **Lesen** | Flamme, Brennerstufe 1/2, Betriebsart Heizung/Warmwasser, Betriebsphase, Laststellung, Pumpe, Störcode, Vorlauf, Wärmeanforderung, Warmwasser, Außentemperatur, Abgas, Ölzähler, Betriebsstunden, Brennerstarts, Zeit seit Wartung, alle Heizkreis-Parameter |
| **Schreiben** | Normal- und Absenk-Raumtemperatur, Heizkurven-Steilheit, Raumfrosttemperatur, Sommer/Winter-Umschaltung, Warmwasser-Soll normal und abgesenkt (Heizkreis 1) |
| **Home Assistant** | 33 MQTT-Sensoren plus Zähler, Laufzeit- und Verbrauchsstatistik (Tag/Monat/Jahr), Schieberegler für die Parameter mit Rückmeldung, fertige Dashboard-Ansicht |
| **Ohne** | WCM-COM, Cloud, Polling einer Weboberfläche |

Getestet mit: **Weishaupt WTC-OB 18-B**, Fernbedienung **WCM-FS** (Version FS 327.30), eBUS Adapter Shield C5 (Firmware 20260917), ebusd 26.1, Home Assistant 2026.10.

> 🔥 **WTC Gas (z. B. WTC 45-A)?** Siehe [docs/07-wtc-gas.md](docs/07-wtc-gas.md): eigene CSV `ebusd/weishaupt-wtc-gas.csv` (`generate_csv.py --variante gas`) mit dem entschlüsselten Status-Broadcast `50 0a` (Flamme, Pumpe, Laststellung, Phase, Vorlauf ohne Abfrage), Ergänzungs-Package `weishaupt_gas.yaml` und Werkzeuge für den passiven Mitschnitt.

## Schnellstart

1. **Hardware**: eBUS-Adapter an die eBUS-Klemmen, an denen auch das WCM-FS hängt, und in dein WLAN bringen → [docs/01-hardware.md](docs/01-hardware.md)
2. **ebusd** in Home Assistant installieren und konfigurieren, `weishaupt-wtc.csv` in den Konfigurationsordner kopieren → [docs/02-installation.md](docs/02-installation.md)
3. **WCM-COM vom Bus trennen** und ebusd mit `--address=ff` starten (nötig zum Schreiben) → [docs/02-installation.md#wcm-com-entfernen](docs/02-installation.md#5-wcm-com-entfernen-und-schreiben-freischalten)
4. **Home-Assistant-Packages** und Dashboard einspielen → [docs/04-home-assistant.md](docs/04-home-assistant.md)

## Inhalt

```
ebusd/weishaupt-wtc.csv               ebusd-Definitionen (Lesen + 422 Schreibtelegramme), erzeugt
ebusd/weishaupt-wtc-gas.csv           WTC Gas: Status-Broadcast 50 0a, Kessel über 50 00 (Fachmann-Parameter), erzeugt
tools/generate_csv.py                 Generator für die CSV inkl. Prüfbyte-Berechnung
homeassistant/packages/weishaupt.yaml           Sensoren, Zähler, Laufzeiten, Anzeigen
homeassistant/packages/weishaupt_parameter.yaml Schieberegler + Automationen zum Schreiben
homeassistant/packages/weishaupt_gas.yaml       WTC Gas: Sensoren aus dem Status-Broadcast, Starts/Laufzeiten
tools/ebus_mitschnitt.py              passiver Mitschnitt (sendet nichts)
tools/ebus_analyse.py                 Auswertung der Mitschnitte, 50 0a als CSV
testdaten/                            WTC 45-A: drei Stunden Mitschnitt, Auslesungen von Seite 2 (50 00)
homeassistant/dashboard/ebus-view.yaml          Dashboard-Ansicht (WCM-COM-Ersatz)
docs/01-hardware.md        Was du brauchst, Anschluss
docs/02-installation.md    Schritt für Schritt
docs/03-protokoll.md       Das Weishaupt-eBUS-Protokoll (Dienste, Adressen, Prüfbyte)
docs/04-home-assistant.md  Packages, Entitäten, Dashboard
docs/05-parameter.md       Tabelle aller bekannten Parameternummern
docs/06-fehlersuche.md     Probleme und Lösungen
docs/07-wtc-gas.md         Variante WTC Gas (WTC 45-A): was gleich ist, was anders
```

## Die wichtigsten Erkenntnisse in Kürze

- Weishaupt nutzt die Dienste **`50 22`** (Parameter lesen) und **`50 23`** (Parameter schreiben). Die Parameternummern sind dieselben „InfoNr“, die auch das WCM-COM in seiner `parameter.json` verwendet.
- Das **erste Datenbyte ist ein Prüfbyte**: CRC8 mit Polynom `0x5C` über alle folgenden Bytes, wobei das letzte Byte nur per XOR eingeht. → [Details](docs/03-protokoll.md#das-prüfbyte)
- Der **WCM-FS übernimmt Schreibbefehle nur von der Absenderadresse `ff`**. Andere Absender bekommen zwar ein ACK, die Änderung wird aber verworfen. ebusd muss deshalb mit `--address=ff` laufen, und das WCM-COM, das ebenfalls `ff` benutzt, muss vom Bus.
- Die **Busspannung kommt nicht vom WCM-COM**. Ohne WCM-COM läuft der Bus unverändert weiter.

## ⚠️ Haftung

Das hier ist ein privates Projekt, ermittelt durch Mitschnitt des Busverkehrs. Weishaupt unterstützt das nicht. Arbeiten an der Heizungselektrik dürfen nur durchgeführt werden, wenn du weißt, was du tust; im Zweifel macht das ein Fachbetrieb. Einstellungen, die du über Home Assistant änderst, wirken direkt auf deine Heizung. Insbesondere bei der Warmwassertemperatur (Legionellenschutz) bist du selbst verantwortlich. Nutzung auf eigene Gefahr, siehe [LICENSE](LICENSE).

## Mitmachen

Du hast eine andere WTC-Variante (WTC-GW, WTC-OB 25/35, zweiter Heizkreis, Pufferspeicher …)? Dann eröffne bitte ein Issue mit einem ebusd-Mitschnitt (`--lograwdata`) und notiere dir parallel, was du im WCM-COM gemacht hast. Mit dem Generator lassen sich neue Parameter in wenigen Minuten ergänzen.

## Danksagung

- [john30/ebusd](https://github.com/john30/ebusd) und die eBUS-Adapter von John Baier
- [J0EK3R/ebusd-configuration-weishaupt](https://github.com/J0EK3R/ebusd-configuration-weishaupt) für die Belegung des Status-Broadcasts `50 0a` der WTC Gas
- [LukasGrebe/ha-addons](https://github.com/LukasGrebe/ha-addons) für die ebusd-App in Home Assistant

---

## English summary

This repository lets you connect a **Weishaupt WTC-OB oil condensing boiler with WCM-FS remote control** to **Home Assistant via eBUS** (eBUS adapter + ebusd + MQTT), replacing the Weishaupt **WCM-COM** gateway.

Key findings (details in [docs/03-protokoll.md](docs/03-protokoll.md), German):

- Weishaupt uses manufacturer services **`50 22`** (read parameter, slave answers 2 bytes LE) and **`50 23`** (write parameter, master-to-master, no response). Parameter numbers ("InfoNr") match the WCM-COM `parameter.json`.
- The **first data byte is a check byte**: CRC8, polynomial `0x5C`, init 0, non-reflected, computed over all following bytes except the last one, which is then XORed in. Reference implementation: [`tools/generate_csv.py`](tools/generate_csv.py).
- Read: `QQ 08 50 22 03 <chk> <nr_lo> <nr_hi>` (boiler) or `QQ 35 …` (heating circuit / WCM-FS).
  Write: `ff 30 50 23 09 <chk> <nr_lo> <nr_hi> <val_lo> <val_hi> 5D 01 00 00` (to WCM-FS master 30).
- The WCM-FS **only accepts writes from source address `ff`**; run ebusd with `--address=ff` and remove the WCM-COM from the bus.
- Because ebusd cannot compute the check byte, the CSV contains one ready-made write message per allowed value (422 in total), generated by the script.

Tested with WTC-OB 18-B, WCM-FS 327.30, eBUS Adapter Shield C5, ebusd 26.1, Home Assistant 2026.10. Use at your own risk. License: MIT.

**Gas variant (WTC 45-A)**: see [docs/07-wtc-gas.md](docs/07-wtc-gas.md). The burner's status broadcast `f1 fe 50 0a` (layout from J0EK3R/ebusd-configuration-weishaupt, confirmed on a WTC 45-A) gives operating phase, flame, gas valves, pump, fault, load, flow temperature and outdoor trend every 30 s without any polling. `generate_csv.py --variante gas` produces `ebusd/weishaupt-wtc-gas.csv`; `weishaupt_gas.yaml` adds the matching Home Assistant entities. On the WTC 45-A the boiler (`08`) does **not** answer `50 22`, but it answers `50 00` (memory read): its IDs use the same check byte, followed by (length-page, address) pairs. Installer parameters P31, P32, P34, P37, P41 and P42 were located on page 2 and are read by `Einstellungen`. Heating-circuit reads and writes (`50 22`/`50 23` to the WCM-FS) work unchanged.
