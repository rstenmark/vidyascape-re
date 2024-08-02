# capture.py
import hashlib
import time
import pyshark
import sqlite3
import spessartine
from spessartine import Net, FilePath, Log
from typing import NoReturn

sender: str = __file__.rpartition("/")[-1].strip()


def setup() -> (sqlite3.Cursor, pyshark.LiveRingCapture):
    Log.log(sender, "Started execution.")

    # sqlite3: Create spessartine.sqlite3 if it does not exist. Then, create any tables that should exist.
    try:
        _ = open(
            FilePath.database, "x+b"
        ).close()  # raises FileExistsError if db_path exists
    except FileExistsError:
        pass

    # sqlite3: Connect to DB, get a cursor
    connection = sqlite3.connect(FilePath.database, timeout=10)
    cursor = connection.cursor()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS capture
        (
            id INTEGER UNIQUE NOT NULL PRIMARY KEY ASC, 
            capture BLOB NOT NULL ON CONFLICT ABORT,
            sizePackets INTEGER NOT NULL ON CONFLICT ABORT,
            blake2b STRING UNIQUE NOT NULL ON CONFLICT ABORT, 
            iso8601 STRING NOT NULL ON CONFLICT ABORT
        );
    """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS packets
        (
            id INTEGER UNIQUE NOT NULL PRIMARY KEY ASC, 
            packet BLOB NOT NULL ON CONFLICT ABORT,
            sizeBytes INTEGER NOT NULL ON CONFLICT ABORT,
            blake2b STRING NOT NULL ON CONFLICT ABORT, 
            iso8601 STRING NOT NULL ON CONFLICT ABORT
        );
    """
    )
    connection.commit()

    # pyshark: Create a capture backed by a finite sized ring buffer
    tcp_bidi_data_only, thirty_two_mb = (
        "host 192.168.1.10 && host 50.116.63.13",
        32 * 1024,
    )
    capture = pyshark.LiveRingCapture(
        interface=Net.interface_name,
        bpf_filter=tcp_bidi_data_only,
        ring_file_size=thirty_two_mb,
        use_json=True,
        include_raw=True,
    )

    return cursor, capture


def teardown(cursor_: sqlite3.Cursor, capture_: pyshark.LiveRingCapture) -> NoReturn:
    # sqlite3: Commit open transactions, hang up.
    cursor_.connection.commit()
    cursor_.connection.close()

    # pyshark: Stop the capture
    capture_.close()

    exit(0)


def mainloop(cursor_: sqlite3.Cursor, capture_: pyshark.LiveRingCapture) -> None:
    timeout = 10.0

    def _callback(packet) -> None:
        raw_packet = packet.get_raw_packet()
        cursor_.execute(
            """
                INSERT OR ABORT INTO packets (packet, sizeBytes, blake2b, iso8601) VALUES (?, ?, ?, ?)
            """,
            (
                raw_packet,
                packet.length,
                hashlib.blake2b(raw_packet).hexdigest(),
                spessartine.Time.now(),
            ),
        )

    t, acc = time.monotonic(), 0
    while True:
        dt = time.monotonic() - t
        if dt >= 10.0:
            Log.log(sender, f"+{acc} packets. ({round(acc/dt, 1)} pkt/s)")
            cursor_.connection.commit()
            t = time.monotonic()
            acc = 0

        try:
            _ = capture_.apply_on_packets(_callback, timeout=timeout, packet_count=1)
            acc += 1

        except KeyboardInterrupt:
            # Exit main loop on CTRL+C
            Log.log(
                sender,
                f"KeyboardInterrupt: Stopping capture.",
            )
            break

        except TimeoutError:
            Log.log(
                sender,
                f"TimeoutError: Capture has been silent for {timeout} seconds. Stopping capture.",
            )
            break

        except Exception as exc:
            Log.log(
                sender,
                f"Exception: An unknown exception occurred: {exc}",
                do_print=False,
            )
            raise


if __name__ == "__main__":
    cur, cap = setup()
    mainloop(cur, cap)
    teardown(cur, cap)
