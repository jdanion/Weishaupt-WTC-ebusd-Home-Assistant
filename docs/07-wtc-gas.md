# 7. Variante WTC Gas (getestet: WTC 45-A)

Ergänzung zu den Kapiteln 1–6, die an einer **WTC-OB (Öl)** entstanden sind.
Hier steht, was an einer **Weishaupt WTC 45-A (Gas-Brennwert)** mit WCM-FS
(ohne WCM-COM) beobachtet wurde, was sich übertragen lässt und was anders ist.

Stand: Oktober 2026, 4 Tage passiver Mitschnitt (25 619 Telegramme, davon
8 363 Status-Broadcasts) mit `tools/ebus_mitschnitt.py`, abgeglichen mit
ESPHome-Anlegefühlern an Vorlauf und Rücklauf und mit dem Wetterdienst.
Adapter: esp-arduino-ebus v7.1 (Port 3334 = nur lesen). Noch **keine
aktiven Abfragen** (`50 22`) an dieser Anlage: die InfoNr der Kessel-Werte
sind für Gas also noch nicht bestätigt.

## Teilnehmer am Bus

| Adresse | Gerät | Kennung (07 04) |
|---|---|---|
| `30` / `35` | WCM-FS (Heizkreisregler) | – |
| `f1` / `f6` | Feuerungsautomat / Heizungsregler im Kessel | `MF=Kromschroeder;ID=WWST1;SW=1200;HW=0401` |
| `08` | Kessel (Parameter-Slave) | `MF=Kromschroeder;ID=W-;SW=1200;HW=0401` |
| `07` | weiteres Gerät, fragt `f6` und `50` mit `09 02` ab (ohne Antwort) | – |
| `03` | weiterer Master (laut ebusd), nicht zugeordnet | – |

Wie bei der WTC-OB: `30 f1 05 07` alle ~10 s (Kesselsollwert), `30 fe 07 00`
jede Minute (Uhrzeit, Außentemperatur), `30 50 50 14` an eine Adresse `50`,
die nie antwortet.

## Was sich übertragen lässt

- **Protokoll und Prüfbyte**: dieselben Dienste `50 22`/`50 23`, dieselbe
  CRC8 (Polynom `0x5C`). Die 30 Schreibtelegramme für Normal- und
  Absenk-Raumtemperatur (15–22 °C), unabhängig erzeugt, sind byte-gleich mit
  denen aus `generate_csv.py`.
- **Heizkreis-Parameter** (`35`/`30`): sie gehören zum WCM-FS, nicht zum
  Brenner. Normal-/Absenk-Raumtemperatur, Steilheit, Sommer/Winter sollten
  daher identisch sein (Bestätigung durch Lesen steht aus).
- **Kessel-InfoNr** (`08`): das WCM-COM nutzt für alle WTC denselben
  Modultyp `10` („WTC HM/WG/WO“), die Nummern sind also sehr
  wahrscheinlich gleich. In der Gas-CSV mit „noch zu bestätigen“ markiert.

## Was anders ist

- Kein Ölzähler, keine Brennerstufe 2 (`Magnetventil2`): in der Gas-Variante
  weggelassen.
- **Status-Broadcast `f1 fe 50 0a`**: bei der WTC-OB „nicht entschlüsselt“.
  Die Belegung für WTC Gas stammt von
  [J0EK3R/ebusd-configuration-weishaupt](https://github.com/J0EK3R/ebusd-configuration-weishaupt)
  (`weishaupt/f6..sc.csv`) und wurde hier an der WTC 45-A bestätigt:

| Byte | Inhalt | Typ | an der WTC 45-A |
|---|---|---|---|
| 0 | Status 1 | UCH | immer `01` |
| 1 | Betriebsphase (i10) | UCH | 0 aus, 2–5 Start, 6 Betrieb, 8 Gasventilkontrolle V2; **12–14** beim Start gesehen (bei J0EK3R Warncodes, hier Bedeutung offen) |
| 2 | Bits: 3 Flamme, 4 Gasventil 1, 5 Gasventil 2, **6 Pumpe**, 7 Störung | BI | `47` aus, `77` Zündung, `7f` Betrieb; **Pumpe immer an** |
| 3 | Bits: 1 Winter, 6 Wärmeanforderung (beobachtet), 7 Umschaltventil Warmwasser | BI | `02` / `42` |
| 4 | Laststellung | UCH, % | 26 im Betrieb (Minimum), bis 73 beim Start |
| 5 | Vorlauftemperatur | D1C | korreliert mit dem Vorlauf-Anlegefühler, r = 0,97, ~1,5 K höher |
| 6 | Abgastemperatur | D1C | `ff` (kein Fühler) |
| 7 | Warmwassertemperatur | D1C | `ff` (kein Speicher am Kessel) |
| 8 | ? | UCH | `00` |
| 9 | Außentemperatur | D1B | = `30 fe 07 00`, ganze Grad |
| 10–11 | Außentemperatur Trend | D2B | z. B. `ce 0b` = 11,80 °C |
| 12 | Vorlauf-Soll | UCH | = Kesselsollwert aus `05 07`, ganze Grad |

Für Home Assistant heißt das: **Flamme, Pumpe, Laststellung, Phase und
Vorlauf kommen ohne eine einzige Abfrage**, alle 30 s, auch mit
`--readonly`. Siehe `homeassistant/packages/weishaupt_gas.yaml`.

## Beobachtungen an der WTC 45-A (Oktober, 10–13 °C außen)

Nur als Beispiel dafür, was der Broadcast zeigt:

- ~32 Brennerstarts pro Tag, im Mittel 15 min Brennerlauf und 28 min Pause,
  fast immer auf Mindestlast (26 %): der Kessel ist für diese Außentemperatur
  zu groß und taktet.
- Vorlauf-Soll ≈ 36 − 0,41 × Außentemperatur (30–35 °C), mit Anhebung
  06–08 Uhr und 16–21 Uhr.
- Spreizung Vorlauf–Rücklauf im Brennerbetrieb ~4 K; in den Pausen läuft
  die Pumpe weiter (Bit 6 und gleiche Vor-/Rücklauftemperatur über 40–60 min).

## Werkzeuge

- `tools/ebus_mitschnitt.py HOST ORDNER`: passiver Mitschnitt über Port
  3334, sendet nichts, läuft neben ebusd.
- `tools/ebus_analyse.py`: Übersicht nach Telegrammtyp, `--folgen` für den
  Verlauf eines Typs, `--status` gibt den `50 0a` als CSV aus.
- `testdaten/wtc45a-2026-10-22-0530-0830.log`: drei Stunden Mitschnitt
  (2 950 Telegramme, 5 Brennerstarts) zum Ausprobieren:

```sh
python3 tools/ebus_analyse.py testdaten/*.log
python3 tools/ebus_analyse.py --status testdaten/*.log | head
```

## Offen

- Kessel-InfoNr per `50 22` an der Gas-Anlage bestätigen (Vorlauf 3101,
  Außen 12, Pumpe 466, Starts 3196/3197, Stunden 3198/3199 …).
- Bedeutung der Phasen 12–14 und der unbenannten Bits.
- Gibt es eine InfoNr für die Pumpendrehzahl oder einen Durchfluss?
