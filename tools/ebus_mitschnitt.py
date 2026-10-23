#!/usr/bin/env python3
"""Passiver eBUS-Mitschnitt, ohne ebusd und ohne zu senden.

Verbindet sich mit dem reinen Lese-Port eines esp-arduino-ebus-Adapters
(Bridge-Modus, Port 3334: was man dorthin sendet, verwirft die Firmware) und
schreibt nie auf den Socket. Eine Zeile pro Telegramm, mit Zeitstempel, eine
Datei pro Tag (~1 MB/Tag):

    2026-10-20T14:40:01.123+02:00 30f1050709bbff26020080ffffff2000

Rohbytes inklusive eBUS-Escaping (a9 00 = a9, a9 01 = aa); ebus_analyse.py
löst es auf. Läuft parallel zu ebusd, ohne es zu stören.

    python3 tools/ebus_mitschnitt.py 192.168.0.64 /srv/ebus-mitschnitt
"""
import datetime
import os
import socket
import sys
import time

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.0.64"
ORDNER = sys.argv[2] if len(sys.argv) > 2 else "./mitschnitt"
PORT = int(os.environ.get("EBUS_PORT", "3334"))
SYN = 0xAA


def schreiben(telegramm: bytes) -> None:
    jetzt = datetime.datetime.now().astimezone()
    pfad = os.path.join(ORDNER, jetzt.strftime("%Y-%m-%d") + ".log")
    with open(pfad, "a") as f:
        f.write(f"{jetzt.isoformat(timespec='milliseconds')} {telegramm.hex()}\n")


def lauschen() -> None:
    with socket.create_connection((HOST, PORT), timeout=10) as s:
        s.settimeout(120)  # der Bus sendet alle ~5 ms ein SYN: 120 s Stille = Störung
        telegramm = bytearray()
        while True:
            daten = s.recv(4096)
            if not daten:
                raise ConnectionError("Verbindung vom Adapter geschlossen")
            for b in daten:
                if b == SYN:
                    if telegramm:
                        schreiben(bytes(telegramm))
                        telegramm.clear()
                else:
                    telegramm.append(b)


def main() -> None:
    os.makedirs(ORDNER, exist_ok=True)
    while True:
        try:
            lauschen()
        except (OSError, ConnectionError) as e:
            print(f"Mitschnitt unterbrochen: {e}; neuer Versuch in 30 s", flush=True)
            time.sleep(30)


if __name__ == "__main__":
    main()
