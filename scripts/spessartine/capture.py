# capture.py

import pyshark
import sqlite3
import datetime
import pathlib
import pickle
import hashlib
import lzma
import logging
from multiprocessing import Process, Queue, TimeoutError


# Common paths
root_path: pathlib.Path = pathlib.Path(__file__).parent.resolve()
db_path = root_path / "capture.sqlite3"
log_path = root_path / "capture.log"

# Configure datetime
tz = datetime.timezone.utc
dt_start = datetime.datetime.now(tz=tz)

# Configure logging
logging.basicConfig(filename=log_path, level=logging.INFO)
logger = logging.getLogger(__name__)


# Configure LZMA compression
if lzma.is_check_supported(lzma.CHECK_SHA256):
    check = lzma.CHECK_SHA256
else:
    logger.warning(
        "lzma: Integrity check SHA256 is not supported by this version of liblzma. Falling back to CRC32."
    )
    check = lzma.CHECK_CRC32

# Configure packet capture
interface = "utun4"
display_filter = "ip.addr==50.116.63.13 and data"
n_packets = 100


def print_and_log(
    logger_: logging.Logger,
    s_: str,
    level: logging.INFO | logging.WARNING | logging.ERROR = logging.INFO,
):
    match level:
        case logging.INFO:
            logger_.info(s_)
        case logging.WARNING:
            logger_.warning(s_)
        case logging.ERROR:
            logger_.error(s_)


def capture(data: Queue, signal: Queue):
    """Captures batches of packets and puts them on the ``data`` queue until ``signal`` queue is not empty.

    Intended for use with ``multiprocessing.Process``:

    p = Process(target=capture, args=(data_queue, signal_queue))
    """
    with pyshark.LiveCapture(
        interface=interface, display_filter=display_filter
    ) as live_capture:
        # Loop until the main process puts something on the signal queue
        while signal.empty():
            # Capture a batch of packets and put them on the data queue
            data.put(live_capture.sniff_continuously(packet_count=n_packets))


if __name__ == "__main__":
    print_and_log(logger, f"Started execution at: {dt_start}")

    # Initialize database
    try:
        _ = open(db_path, "x+b").close()  # raises FileExistsError if db_path exists
        print_and_log(logger, f"Initializing database file: {db_path}")
        with sqlite3.connect(db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS capture
                (
                    id INTEGER UNIQUE NOT NULL PRIMARY KEY ASC, 
                    capture BLOB NOT NULL ON CONFLICT ABORT, 
                    blake2b STRING UNIQUE NOT NULL ON CONFLICT ABORT, 
                    iso8601 STRING NOT NULL ON CONFLICT ABORT
                );
            """
            )
            con.commit()
    except FileExistsError:
        # Database already initialized, skip step
        pass

    # Start capturing batches of packets in a separate process.
    print_and_log(
        logger,
        f'Beginning live capture: interface="{interface}", display_filter="{display_filter}"',
    )
    data_queue, signal_queue = Queue(maxsize=128), Queue(maxsize=1)
    p = Process(target=capture, args=(data_queue, signal_queue))
    p.start()

    # Consume batches of packets until KeyboardInterrupt raised.
    while True:
        try:
            # Block until a batch of packets has been put on the data queue
            packets = [packet for packet in data_queue.get(block=True)]

            # Pickle and then compress batch
            compressor = lzma.LZMACompressor(
                format=lzma.FORMAT_XZ, check=check, preset=9
            )
            capture_pickle_xz = (
                compressor.compress(pickle.dumps(packets)) + compressor.flush()
            )

            # Hash compressed pickle
            blake2b = hashlib.blake2b(capture_pickle_xz).hexdigest()[1:]

            # Write batch to disk
            s = f"Writing capture to disk: {len(packets)} packets, {len(capture_pickle_xz)} bytes, blake2b={blake2b}"
            logger.info(s)
            print(s)
            with sqlite3.connect(db_path) as con:
                con.execute(
                    "INSERT OR ABORT INTO capture (capture, blake2b, iso8601) VALUES (?, ?, ?)",
                    (capture_pickle_xz, blake2b, str(dt_start)),
                )
                con.commit()
        except KeyboardInterrupt:
            # Signal child process to terminate
            signal_queue.put(0)
            s = f"KeyboardInterrupt: Signalled child processes to terminate."
            logger.info(s)
            print(s)
            timeout = 10
            # Block until child process terminated
            try:
                s = f"Waiting {timeout} seconds for child processes to terminate..."
                logger.info(s)
                print(s)
                p.join(timeout=timeout)
            except TimeoutError:
                s = f"TimeoutError: Child process termination timed out. Forcibly terminating children."
                logger.warning(s)
                print(s)
                p.terminate()
            # Break out of infinite loop, exit main process
            break
