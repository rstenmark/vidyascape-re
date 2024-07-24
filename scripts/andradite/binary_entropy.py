import os
import multiprocessing as mp
import statistics
import math
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from typing import Literal
from time import perf_counter_ns


_chunksize = None


class Perf(object):
    def __init__(self):
        self.state: dict[str, int] = {}
        self._reset()

    def _reset(self, silent=True) -> None:
        new_ts = perf_counter_ns()
        self.state = {
            "ts": new_ts,
            "te": new_ts,
            "delta": 0,
            "lap": 0,
        }
        if not silent:
            print(self)
        return

    def _read(self, silent=True) -> dict[str, int]:
        new_te = perf_counter_ns()
        new_delta = new_te - self.state["ts"]
        self.state["te"] = new_te
        self.state["delta"] = new_delta
        self.state["lap"] += 1
        if not silent:
            print(self)
        return self.state

    def __call__(
        self, mode: Literal["read", "reset", "read_reset"], silent=True
    ) -> dict[str, int] | None:
        assert mode in ("read", "reset", "read_reset")
        if mode == "read":
            return self._read(silent)
        elif mode == "reset":
            return self._reset(silent)
        elif mode == "read_reset":
            ret = self._read(silent)
            self._reset(silent=True)
            return ret
        else:
            raise ValueError('mode must be one of "read", "reset", or "read_reset"')

    def __str__(self):
        def ns_to_ms(nanoseconds: int) -> float:
            return round(nanoseconds / 10**6, 3)

        return "\n".join(
            (
                f"Lap: {self.state["lap"]}",
                # f"Started-At: {ns_to_ms(self.state["ts"])} milliseconds",
                # f"Sampled-At: {ns_to_ms(self.state["te"])} milliseconds",
                f"Delta: {ns_to_ms(self.state["delta"])} milliseconds",
            )
        )


class Loader(object):
    def __init__(self):
        self._root_path = Path("/Users/ryan/.vscape2/")
        self._cache: dict[Path, bytes] = {}

    def load(self, filename: str) -> bytes:
        path_to_file = self._root_path / filename
        try:
            return self._cache[path_to_file]
        except KeyError:
            with open(path_to_file, "rb") as fd:
                if fd.tell() == fd.seek(0, os.SEEK_END):
                    raise RuntimeError(f"{path_to_file} is empty.")
                else:
                    fd.seek(0, os.SEEK_SET)
                try:
                    self._cache[path_to_file] = fd.read(-1)
                    return self._cache[path_to_file]
                except IOError as e:
                    e.add_note(f"Failed to load {str(path_to_file)}")

    def get_cache_version(self) -> bytes:
        return self.load("cacheVersion.dat")

    def get_main_file_cache(
        self, index: None | int = None, file_extension: Literal["idx", "dat"] = "idx"
    ) -> bytes:
        if isinstance(index, int):
            if index < 0 or index > 255:
                raise ValueError("index must be [0, 256).")
        elif index is not None:
            raise TypeError("index must be int or None.")

        if file_extension not in ("idx", "dat"):
            raise ValueError('file_extension must be "idx" or "dat".')

        if index is None:
            return self.load("main_file_cache." + file_extension)
        else:
            return self.load("main_file_cache." + file_extension + str(index))


class Entropy:
    class Kernels:

        @staticmethod
        def batched_binary_probability(_bytes: list[int]) -> list[float]:
            return [byte.bit_count() / 0xFF for byte in _bytes]

        @staticmethod
        def batched_binary_entropy(ps: list[float]) -> list[float]:
            return [
                (
                    0.0
                    if p == 0.0 or p == 1.0
                    else -p * math.log2(p) - (1 - p) * math.log2(1 - p)
                )
                for p in ps
            ]

    @staticmethod
    def make_batches(l: bytes | list, batch_size=1024) -> list[list]:
        num_batches = len(l) // batch_size
        tail = batch_size * num_batches
        batches = [
            l[ii * batch_size : (ii + 1) * batch_size] for ii in range(num_batches)
        ]
        batches.append(l[tail:])
        return batches

    @staticmethod
    def binary_batched(
        input_bytes: bytes, batch_size: int = 1024, chunksize=None
    ) -> list[float]:
        with mp.Pool() as pool:
            data = Entropy.make_batches(input_bytes, batch_size)
            probabilities = pool.map(
                Entropy.Kernels.batched_binary_probability, data, chunksize=chunksize
            )
            entropies = pool.map(
                Entropy.Kernels.batched_binary_entropy,
                probabilities,
                chunksize=chunksize,
            )
        entropies_flattened = []
        for _list in entropies:
            for h in _list:
                entropies_flattened.append(h)
        return entropies_flattened


def _binning_kernel_mean(_slice: list[float]) -> float:
    return statistics.mean(_slice)


def _binning_kernel_sum(_slice: list[float]) -> float:
    return sum(_slice)


def _binning_kernel_variance(_slice: list[float]) -> float:
    return statistics.variance(_slice)


def main():
    event_perf, overall_perf = Perf(), Perf()

    overall_perf(mode="reset")
    print("[=] Loading file")
    event_perf(mode="reset")
    loader = Loader()
    cache_file_bytes = loader.get_main_file_cache(index=1, file_extension="idx")
    event_perf(mode="read_reset", silent=False)

    print("[=] Calculating binary entropy")
    res = Entropy.binary_batched(
        cache_file_bytes,
        batch_size=16384,
        chunksize=None,
    )
    event_perf(mode="read_reset", silent=False)

    plt.style.use("dark_background")
    fig, ax1 = plt.subplots()

    print("[=] Binning results")
    bins = {}
    count_bins = 1024
    stride = len(res) // count_bins
    tail = stride * count_bins
    slices = [res[stride * ii : stride * (ii + 1)] for ii in range(count_bins)]
    slices.append(res[tail:])
    with mp.Pool() as pool:
        bins["mean"] = pool.map(_binning_kernel_sum, slices, chunksize=_chunksize)

    ax1.set(
        xlim=(0, count_bins),
        xticks=np.arange(1, count_bins, count_bins // 32),
    )

    ax1.stairs(bins["mean"], linewidth=1.5, fill=True)

    event_perf(mode="read_reset", silent=False)
    overall_perf(mode="read_reset", silent=False)

    print("[+] Done.")

    plt.show()


if __name__ == "__main__":
    main()
