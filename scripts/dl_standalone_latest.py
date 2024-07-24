from typing import NoReturn
import sqlite3 as sql
import requests
import hashlib
import lzma
from random import sample

# Enable mock return values for certain functions
_mock_mode: bool = False
if _mock_mode:
    print("*** MOCK MODE ENABLED ***")

_db_uri = "file:dl_standalone_latest.sqlite3?mode=rwc"
_dl_url = """https://vidyascape.org/files/client/vidyascape.jar"""


def get_jar(mock=False) -> bytes:
    if not mock:
        try:
            resp = requests.get(_dl_url)
            resp.raise_for_status()
            print(f"Response Code {resp.status_code}, ", end="")
            return resp.content
        except requests.exceptions.RequestException as e:
            e.add_note(f"Failed to download the jar.")
    else:
        with sql.connect(_db_uri, uri=True) as con:
            cur = con.cursor()
            # Choose a random jar from the 10 most-recent
            ret = [
                t[0]
                for t in con.execute("""SELECT jarBlob FROM jars LIMIT 10""").fetchall()
            ]
            ret = sample(ret, k=1)[0]
            con.commit()
            cur.close()
        return lzma.decompress(ret)


def main() -> NoReturn:
    if not lzma.is_check_supported(lzma.CHECK_SHA256):
        raise AssertionError(
            "Your version of liblzma lacks support for the lzma.CHECK_SHA256 integrity check type."
        )

    try:
        print("Getting the jar... ", end="")
        jar_blob = get_jar(mock=_mock_mode)
        assert jar_blob is not None
        print(" done.")
    except requests.exceptions.RequestException as e:
        e.add_note(f"Failed to download the jar.")
        raise
    except KeyboardInterrupt:
        raise

    try:
        size_bytes_uncompressed = len(jar_blob)
        blake2b_hex = hashlib.blake2b(
            jar_blob,
            digest_size=16,
        ).hexdigest()
        assert size_bytes_uncompressed is not None
        assert blake2b_hex is not None
        assert size_bytes_uncompressed != 0
        assert len(blake2b_hex) == 32
        print(f"vidyascape.jar {size_bytes_uncompressed} {blake2b_hex}")
    except KeyboardInterrupt:
        raise
    except Exception as e:
        e.add_note("Failed to hash the jar.")
        raise

    try:
        print("LZMA compressing the jar... ")
        jar_blob_lzma = lzma.compress(
            data=jar_blob,
            format=lzma.FORMAT_XZ,
            check=lzma.CHECK_SHA256,
            preset=9 | lzma.PRESET_EXTREME,
        )
        size_bytes_compressed = len(jar_blob_lzma)
        print(
            f"{size_bytes_uncompressed} bytes -> {size_bytes_compressed} bytes ({round(100 * (1-(size_bytes_compressed / size_bytes_uncompressed)), ndigits=3)}% compressed, abs. change: {size_bytes_compressed-size_bytes_uncompressed} bytes)"
        )
        print(f"done.")
    except KeyboardInterrupt:
        raise
    except lzma.LZMAError as e:
        e.add_note("Failed to lzma compress the jar.")
        raise

    try:
        print("Transacting with DB...", end="")
        with sql.connect(database=_db_uri, uri=True) as con:
            cur = con.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS jars 
                (
                    jarID INTEGER PRIMARY KEY ASC AUTOINCREMENT,
                    jarBlob BLOB NOT NULL ON CONFLICT ABORT,
                    sizeBytes INTEGER NOT NULL ON CONFLICT ABORT,
                    blake2b TEXT UNIQUE ON CONFLICT ABORT
                );
                """
            )
            con.commit()
            cur.execute(
                "INSERT OR ABORT INTO jars (jarBlob, sizeBytes, blake2b) VALUES (?, ?, ?)",
                (
                    jar_blob_lzma,
                    size_bytes_uncompressed,
                    blake2b_hex,
                ),
            )
            con.commit()
            cur.close()
        print(" done.")
    except sql.IntegrityError as e:
        print(
            f" done.\nThere was not a newer version available, or an error occurred:\n>\t{e.sqlite_errorname}: \
{e.sqlite_errorcode}"
        )
    except sql.Error as e:
        e.add_note("Failed when accessing dl_standalone_latest.sqlite3.")
        raise
    except KeyboardInterrupt:
        raise

    print("Operation complete.")
    exit()


if __name__ == "__main__":
    main()
