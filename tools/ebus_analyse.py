#!/usr/bin/env python3
"""Auswertung der Mitschnitte von ebus_mitschnitt.py.

    python3 tools/ebus_analyse.py mitschnitt/*.log                    # Übersicht
    python3 tools/ebus_analyse.py --folgen 30f10507 mitschnitt/*.log  # Verlauf eines Typs
    python3 tools/ebus_analyse.py --status mitschnitt/*.log > s.csv   # 50 0a als CSV

Ein eBUS-Telegramm: QQ ZZ PB SB NN Daten CRC, dann bei einem Slave als Ziel
ACK + NN' Daten' CRC' + ACK. Broadcast (ZZ = fe): kein ACK.

--status dekodiert den Status-Broadcast f1 fe 50 0a einer WTC Gas
(Belegung siehe docs/07-wtc-gas.md) in eine CSV-Zeile pro Telegramm, zum
Abgleich mit eigenen Fühlern oder für Diagramme.
"""
import argparse
import collections
import sys

MASTER = {0x00, 0x10, 0x30, 0x70, 0xF0, 0x01, 0x11, 0x31, 0x71, 0xF1,
          0x03, 0x13, 0x33, 0x73, 0xF3, 0x07, 0x17, 0x37, 0x77, 0xF7,
          0x0F, 0x1F, 0x3F, 0x7F, 0xFF}


def entescapen(b: bytes) -> bytes:
    aus, i = bytearray(), 0
    while i < len(b):
        if b[i] == 0xA9 and i + 1 < len(b):
            aus.append(0xA9 if b[i + 1] == 0x00 else 0xAA)
            i += 2
        else:
            aus.append(b[i])
            i += 1
    return bytes(aus)


def zerlegen(t: bytes):
    """(qq, zz, pbsb, Masterdaten, Slaveantwort oder None, Zustand)."""
    if len(t) < 6:
        return None
    qq, zz, pb, sb, nn = t[:5]
    pbsb = f"{pb:02x}{sb:02x}"
    if len(t) < 6 + nn:
        return (qq, zz, pbsb, t[5:], None, "abgeschnitten")
    daten, rest = t[5:5 + nn], t[6 + nn:]
    if zz == 0xFE:
        return (qq, zz, pbsb, daten, None, "Broadcast")
    if not rest:
        return (qq, zz, pbsb, daten, None, "ohne Antwort")
    if rest[0] != 0x00:
        return (qq, zz, pbsb, daten, None, f"NAK {rest[0]:02x}")
    if zz in MASTER:
        return (qq, zz, pbsb, daten, None, "Master-Master")
    if len(rest) < 2:
        return (qq, zz, pbsb, daten, None, "Slave stumm")
    return (qq, zz, pbsb, daten, rest[2:2 + rest[1]], "Antwort")


def lesen(dateien):
    for pfad in dateien:
        with open(pfad) as f:
            for zeile in f:
                try:
                    zeit, hexa = zeile.split()
                    yield zeit, entescapen(bytes.fromhex(hexa))
                except ValueError:
                    continue


def temp_d1c(b):
    return "" if b == 0xFF else f"{b / 2:.1f}"


def status_csv(dateien):
    print("zeit,phase,flamme,gasventil1,gasventil2,pumpe,stoerung,winter,anforderung,"
          "laststellung,vorlauf,abgas,warmwasser,aussen,aussen_trend,vorlauf_soll")
    for zeit, t in lesen(dateien):
        z = zerlegen(t)
        if not z or z[0] != 0xF1 or z[2] != "500a" or len(z[3]) < 13:
            continue
        d = z[3]
        bit = lambda byte, n: (byte >> n) & 1
        aussen = d[9] - 256 if d[9] > 127 else d[9]
        trend = int.from_bytes(d[10:12], "little", signed=True) / 256
        print(f"{zeit},{d[1]},{bit(d[2], 3)},{bit(d[2], 4)},{bit(d[2], 5)},{bit(d[2], 6)},{bit(d[2], 7)},"
              f"{bit(d[3], 1)},{bit(d[3], 6)},{d[4]},{temp_d1c(d[5])},{temp_d1c(d[6])},{temp_d1c(d[7])},"
              f"{aussen},{trend:.2f},{d[12]}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("dateien", nargs="+")
    p.add_argument("--folgen", help="QQZZPBSB, z. B. 30f10507: nur Änderungen dieses Typs ausgeben")
    p.add_argument("--status", action="store_true", help="f1 fe 50 0a (WTC Gas) als CSV ausgeben")
    a = p.parse_args()
    if a.status:
        return status_csv(a.dateien)

    typen, werte, erste, letzte, vorher = collections.Counter(), collections.defaultdict(set), None, None, {}
    for zeit, t in lesen(a.dateien):
        z = zerlegen(t)
        if not z:
            continue
        erste, letzte = erste or zeit, zeit
        qq, zz, pbsb, daten, antwort, zustand = z
        schluessel = f"{qq:02x}{zz:02x}{pbsb}"
        if pbsb in ("5022", "5023") and daten:
            schluessel += f" {daten[:3].hex()}"  # Weishaupt: Prüfbyte + InfoNr
        typen[(schluessel, zustand)] += 1
        v = (daten.hex(), antwort.hex() if antwort else "")
        werte[schluessel].add(v)
        if a.folgen and schluessel.startswith(a.folgen) and vorher.get(schluessel) != v:
            print(zeit, schluessel, *v)
            vorher[schluessel] = v
    if a.folgen:
        return
    print(f"von {erste} bis {letzte}\n")
    print(f"{'Typ QQZZPBSB':28} {'Zustand':16} {'Anzahl':>7} {'versch. Werte':>14}")
    for (schluessel, zustand), n in typen.most_common():
        print(f"{schluessel:28} {zustand:16} {n:7} {len(werte[schluessel]):14}")
    schreib = [k for (k, _) in typen if k[4:8] == "5023"]
    print("\nWeishaupt-Schreibtelegramme (50 23):", schreib or "keine")


if __name__ == "__main__":
    sys.exit(main())
