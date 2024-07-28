# capture.py

import pathlib
import time

import pyshark
import sqlite3
import logging
import spessartine
from spessartine import pack
from multiprocessing import Process, Queue, TimeoutError


# def capture(
#     data: Queue, signal: Queue, display_filter="ip.addr==50.116.63.13 and data"
# ):
#     """Captures batches of packets and puts them on the ``data`` queue until ``signal`` queue is not empty.
# 
#     Intended for use with ``multiprocessing.Process``:
# 
#     p = Process(target=capture, args=(data_queue, signal_queue))
#     """
#     with pyshark.LiveCapture(
#         interface=spessartine.Net.interface_name, display_filter=display_filter
#     ) as live_capture:
#         # Loop until the main process puts something on the signal queue
#         #  while signal.empty():
#         try:
#             #
#             for packet in live_capture.sniff_continuously(packet_count=)
#                 [packet for packet in live_capture.sniff_continuously(packet_count=10)]
#             )
#         except KeyboardInterrupt:
#             break


if __name__ == "__main__":
    sender = pathlib.Path(__file__).name
    spessartine.Log.log(sender, "Started execution.")

    # Initialize database
    try:
        _ = open(
            spessartine.FilePath.database, "x+b"
        ).close()  # raises FileExistsError if db_path exists
        spessartine.Log.log(
            sender, f"Initializing database file: {spessartine.FilePath.database}"
        )
        with sqlite3.connect(spessartine.FilePath.database) as con:
            con.execute(
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
            con.commit()
    except FileExistsError:
        # Database already initialized, skip step
        pass

    # sqlite3: Connect to DB, get a cursor
    con = sqlite3.connect(spessartine.FilePath.database, timeout=10)
    cur = con.cursor()

    # pyshark: Create a capture using a ring buffer
    tcp_bidi_data_only, thirty_two_MB = "ip.addr==50.116.63.13 and data", 32 * 1024
    live_capture = pyshark.LiveRingCapture(interface=spessartine.Net.interface_name, display_filter=tcp_bidi_data_only, ring_file_size=thirty_two_MB)
    del tcp_bidi_data_only, thirty_two_MB


    poll_rate_s = 1 / 16
    while True:
        try:
            tick = time.monotonic()



            tock = time.monotonic()
            time.sleep(max(poll_rate_s, poll_rate_s - (tock -  tick)))
        except KeyboardInterrupt:
            # pyshark: Stop the capture
            live_capture.close()

    # sqlite3: Commit any pending transactions then close connection
    con.commit()
    con.close()

    with sqlite3.connect(spessartine.FilePath.database) as con:
        with pyshark.LiveCapture(
                interface=spessartine.Net.interface_name, display_filter="ip.addr==50.116.63.13 and data"
        ) as live_capture:
        while True:
            try:

                buffer = []
                while len(buffer) < 100:
                    # Block until a batch of packets has been put on the data queue.
                    buffer.extend(data_queue.get(block=True))

                # Pickle, compress batch. Compute blake2b hash of pickled, compressed batch.
                xz, digest = pack(buffer, do_compress=False)
                # Write batch to disk
                spessartine.Log.log(
                    sender,
                    f"Writing capture to disk: {len(buffer)} packets, {len(xz)} bytes, blake2b={digest}",
                )
                con.execute(
                    "INSERT OR ABORT INTO capture (capture, sizePackets, blake2b, iso8601) VALUES (?, ?, ?, ?)",
                    (xz, len(buffer), digest, spessartine.Time.now()),
                )
                con.commit()
            except KeyboardInterrupt:
                # Signal child process to terminate
                signal_queue.put(0)
                spessartine.Log.log(
                    sender,
                    f"KeyboardInterrupt: Signalled child processes to terminate.",
                )
                # Block until child process terminated
                try:
                    p.join(timeout=10)
                except TimeoutError:
                    spessartine.Log.log(
                        sender,
                        f"TimeoutError: Child process termination timed out. Forcibly terminating children.",
                        level=logging.WARNING,
                    )
                    p.terminate()
                # Break out of infinite loop, exit main process
                break
