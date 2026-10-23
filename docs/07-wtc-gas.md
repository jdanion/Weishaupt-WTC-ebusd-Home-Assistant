# 7. Variante WTC Gas (getestet: WTC 45-A)

Ergänzung zu den Kapiteln 1–6, die an einer **WTC-OB (Öl)** entstanden sind.
Hier steht, was an einer **Weishaupt WTC 45-A (Gas-Brennwert)** mit WCM-FS
(ohne WCM-COM) beobachtet wurde, was sich übertragen lässt und was anders ist.

Stand: Oktober 2026, 4 Tage passiver Mitschnitt (25 619 Telegramme, davon
8 363 Status-Broadcasts) mit `tools/ebus_mitschnitt.py`, abgeglichen mit
ESPHome-Anlegefühlern an Vorlauf und Rücklauf und mit dem Wetterdienst.
Adapter: esp-arduino-ebus v7.1 (Port 3334 = nur lesen, Port 3335 enhanced für
ebusd mit `--address=ff`). Danach aktive Abfragen (`50 22`, `50 00`) und eine
Schreibprobe, siehe unten.

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

- **Protokoll und Prüfbyte**: dieselben Dienste `50 22`/`50 23` zum WCM-FS,
  dieselbe CRC8 (Polynom `0x5C`). Die Schreibtelegramme aus
  `generate_csv.py` funktionieren unverändert.
- **Heizkreis-Parameter** (`35`/`30`) **bestätigt**: alle InfoNr aus Kapitel 5
  antworten an der WTC 45-A. `Vorlaufsoll` (InfoNr 2) = 32,2 °C, gleich dem
  Kesselsollwert im Broadcast `05 07` (32,19 °C). Gelesene Werte: Normal 18,5 °C,
  Absenk 16,5 °C, Steilheit 10,0, Raumfrost 10 °C, Sommer/Winter 20 °C,
  Betriebsart 11.
- **Schreiben bestätigt**: `SetRaumsoll_175` (18,5 → 17,5 °C) von `ff` aus,
  Nachlesen 17,5; der Kesselsollwert im `05 07` fiel sofort von 32,19 auf
  30,13 °C (Außen 9 °C). Eine Änderung am WCM-FS selbst (Sommer/Winter 20 → 16)
  war beim nächsten Poll (≤ 1 min) sichtbar.

## Was anders ist

- **Der Kessel (`08`) beantwortet `50 22` nicht**: 176 Abfragen ohne ACK,
  obwohl er `07 04` (Kennung) beantwortet. Die Kessel-InfoNr aus Kapitel 5
  (Vorlauf, Flamme, Starts …) gibt es hier also nicht; die Gas-CSV liest den
  Kessel stattdessen über den Status-Broadcast und über `50 00` (siehe unten).
- Kein Ölzähler, keine Brennerstufe 2.
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

## Dienst `50 00`: Speicher des Feuerungsautomaten lesen

J0EK3R liest den Kessel mit `50 00` und festen IDs. An der WTC 45-A zeigte
sich: **diese IDs tragen dasselbe Prüfbyte wie `50 22`/`50 23`**, nachgerechnet
an allen 11 ID-Formen aus seinen Dateien. Dahinter folgen Paare
`(LP, Adresse)`: L+1 = Anzahl Bytes (1…16), P = Speicherseite. Die Antwort
ist ein Statusbyte, gefolgt von den Daten. Damit lässt sich jede Adresse
berechnen (`id_5000()` in `generate_csv.py`):

```
ff 08 50 00 03  c1 62 3d     → 08  00 3c 1e 14 32 13 0f 18   (Seite 2 ab 0x3d, 7 Bytes)
ff 08 50 00 09  bc 11 62 01 65 11 70 01 74 → 07  00 00 00 00 32 31 01  (Seite 1, Gebläse 3000/2940 1/min)
```

Seite 1 enthält Prozesswerte, Seite 2 Einstellungen. Lesen ist
unproblematisch: drei Lesungen nach J0EK3R und drei vollständige Auslesungen
von Seite 2 (je 32 × 8 Bytes, alle 2–3 s) ohne jede Auffälligkeit im
Brennerstatus.

### Fachmann-Parameter auf Seite 2

Seite 2 wurde vor und nach Änderungen am Bedienteil des Kessels ausgelesen
(Fachmann-Ebene, Code 11; je eine Stufe ändern, dann zurück). Ergebnis:

| Adresse | Parameter | Kodierung | Probe |
|---|---|---|---|
| 0x17 | P31 max. Vorlauftemperatur | °C direkt | 78 → 77 → 78 |
| 0x18 | P32 Schaltdifferenz Vorlauf | K direkt | 3 → 6 |
| 0x19 | P34 Brennertaktsperre | unteres Halbbyte, min | 5 → 15, 12 → `0xec` |
| 0x1e | P37 max. Leistung Heizbetrieb | Skala 0–255 | 255 → 252 (99 %) → 255 |
| 0x1f | P41 Pumpennachlaufzeit | min direkt | 3 → 4 → 3 |
| 0x20 | P42 min. Leistung Pumpe | % direkt | 50 → 51 → 50 |

Vermutet, nicht geprüft: 0x1c/0x1d = 68 = 27 % von 255 (P36 minimale
Leistung). Bei jeder Änderung änderte sich zusätzlich ein Byte weiter hinten
(0xeb, 0xf0: Zähler?) bzw. 0x3c (Prüfsumme?). Ab 0x3d stehen die
Endkunden-Werte des Kessels (wirksam nur ohne WCM-FS). Eine Änderung am
Kessel erzeugt **kein** Telegramm auf dem Bus: man sieht sie nur durch Lesen.

`Einstellungen` in der Gas-CSV liest 0x17–0x20 in einer Abfrage (ohne
Poll-Priorität); z. B. einmal täglich per Timer:
`ebusctl read -f -c wtc Einstellungen`. Die Sensoren dazu stehen in
`weishaupt_gas.yaml`. Rohauszüge von Seite 2: `testdaten/wtc45a-seite2-*.txt`.

Bestätigt nebenbei: A8 „Kesselleistung bei Zündung“ (Werk 73 %) ist genau die
Laststellung, die der Broadcast beim Start zeigt (72–73 %).

## Beobachtungen an der WTC 45-A (Oktober, 10–13 °C außen)

Nur als Beispiel dafür, was der Broadcast zeigt:

- ~32 Brennerstarts pro Tag, im Mittel 15 min Brennerlauf und 28 min Pause,
  fast immer auf Mindestlast (26 %): der Kessel ist für diese Außentemperatur
  zu groß und taktet.
- Vorlauf-Soll ≈ 36 − 0,41 × Außentemperatur (30–35 °C), mit Anhebung
  06–08 Uhr und 16–21 Uhr.
- Spreizung Vorlauf–Rücklauf im Brennerbetrieb ~4 K; in den Pausen läuft
  die Pumpe weiter (Bit 6 und gleiche Vor-/Rücklauftemperatur über 40–60 min).
  Laut Anleitung läuft sie im Normalbetrieb mit Außenfühler unabhängig von
  P40 dauernd, bei abgeschaltetem Brenner mit P42 (hier vom Installateur auf
  50 % gestellt, Werk 40 %).
- Gegen das Takten: P32 von 3 auf 6 K und P34 auf 15 min gestellt (die
  Mindestleistung P36 lässt sich nicht weiter senken, 10 kW). Ergebnis folgt.

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

- Wirkung von P32 = 6 K auf die Zahl der Brennerstarts (vorher ~32/Tag).
- Bedeutung der Phasen 12–14, der unbenannten Bits, von 0x1a–0x1d und 0x3c.
- Weitere Fachmann-Parameter auf Seite 2 (P30, P33, P35, P36, P38, P40, P43–P45).
- Gibt es eine Adresse für Pumpendrehzahl oder Durchfluss?
