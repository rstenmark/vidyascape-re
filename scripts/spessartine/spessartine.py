# spessartine.py

import lzma
import pickle
import pathlib
import datetime
import logging
from hashlib import blake2b
from typing import Any


class FilePath:
    root: pathlib.Path = pathlib.Path(__file__).parent.resolve()
    database = root / "spessartine.sqlite3"
    log = root / "spessartine.log"


class Net:
    interface_name: str = "enp34s0"


class Time:
    timezone = datetime.timezone.utc

    @staticmethod
    def now() -> str:
        return str(datetime.datetime.now(tz=Time.timezone))


class Log:
    logging.basicConfig(filename=FilePath.log, level=logging.INFO)
    logger = logging.getLogger(pathlib.Path(__file__).name)

    @staticmethod
    def log(
        sender: str,
        message: str,
        do_print: bool = True,
        level: logging.INFO | logging.WARNING | logging.ERROR = logging.INFO,
    ) -> None:
        assert isinstance(sender, str)
        assert isinstance(message, str)
        assert len(sender) > 0
        assert len(message) > 0
        assert isinstance(do_print, bool)
        assert level in {0, 10, 20, 30, 40, 50}

        message = f"{Time.now()}:{sender.strip()}: {message.strip()}"
        match level:
            case logging.INFO:
                Log.logger.info(message)
            case logging.WARNING:
                Log.logger.warning(message)
            case logging.ERROR:
                Log.logger.error(message)

        if do_print:
            print(message)


def pack(obj, do_compress=True, compression_preset=6) -> tuple[bytes, str]:
    """
    Pickles ``obj`` and then [optionally] LZMA compresses the pickle. Returns a tuple containing the [compressed] pickle and its
    blake2b hash.

    :raises pickle.PicklingError:
    :raises lzma.LZMAError:
    :raises AssertionError:
    """

    assert pickle.HIGHEST_PROTOCOL >= 5

    ret = pickle.dumps(obj, protocol=5)

    if do_compress:
        assert isinstance(compression_preset, int)
        assert 9 >= compression_preset >= 0
        assert lzma.is_check_supported(lzma.CHECK_SHA256)
        ret = lzma.compress(
            ret,
            format=lzma.FORMAT_XZ,
            check=lzma.CHECK_SHA256,
            preset=lzma.PRESET_EXTREME | compression_preset,
        )

    return ret, blake2b(ret).hexdigest()


def unpack(obj: bytes, do_decompress=True) -> Any:
    """
    Takes an LZMA compressed pickle ``obj``. Returns a decompressed, un-pickled ``obj``.

    :raises pickle.UnpicklingError:
    :raises lzma.LZMAError:
    """
    if do_decompress:
        return pickle.loads(lzma.decompress(obj, format=lzma.FORMAT_XZ))
    else:
        pickle.loads(obj)
