from typing import NoReturn
from pathlib import Path
from collections import defaultdict
from math import log2
import matplotlib.pyplot as plt
from typedef import Bits, Bytes


class Loader(object):
    def __init__(self, path_to_cache: Path):
        assert isinstance(path_to_cache, Path)
        self.cache_root_path = path_to_cache
        self.data: dict[Path, bytes] = {}

    def _lazy_load(self, path) -> bytes:
        try:
            return self.data[path]
        except KeyError:
            try:
                with open(path, "rb") as fd:
                    ret = fd.read()
                assert ret is not None
                self.data[path] = ret
                return ret
            except FileNotFoundError as e:
                e.add_note(
                    f"The file could not be found. Is {self.cache_root_path} \
the correct path to the VScape cache directory?"
                )

    def get_cache_version(self) -> bytes:
        return self._lazy_load(self.cache_root_path / "cacheVersion.dat")

    def get_sprites_idx(self) -> bytes:
        return self._lazy_load(self.cache_root_path / "sprites/sprites.dat")

    def get_sprites_dat(self) -> bytes:
        return self._lazy_load(self.cache_root_path / "sprites/sprites.idx")


loader = Loader(path_to_cache=Path("/Users/ryan/.vscape2/"))


def main() -> NoReturn:
    sprites_idx = loader.get_sprites_idx()

    # length = len(sprites_idx)
    # count = defaultdict(f := lambda: 1)
    # for byte in sprites_idx:
    #     count[byte] += 1
    #
    # min_count, max_count = min(count.values()), max(count.values())
    #
    # count_normalized = {k: v / max_count for k, v in count.items()}
    # information = {k: log2(1 / v) for k, v in count_normalized.items()}
    #
    # x = range(1, length + 1)
    # y = [information[b] for b in sprites_idx]

    d = {}
    len_sprites_idx = len(sprites_idx)
    for idx, b in enumerate(sprites_idx):
        if b not in d.keys():
            d[b] = {}
        if idx + 1 <= len_sprites_idx - 1:
            next_b = sprites_idx[idx + 1]
            if next_b not in d[b].keys():
                d[b][next_b] = 1
            else:
                d[b][next_b] += 1
        else:
            pass

    for k in d.keys():
        for kk in d[k].keys():
            m = max(d[k].values())
            c = len(d[k].values())
            # print(d[k], d[k][kk], d[k][kk] / m)
            d[k][kk] = 1 - (d[k][kk] / m / c)

    surprise = []
    for idx, b in enumerate(sprites_idx):
        if idx + 1 <= len_sprites_idx - 1:
            next_b = sprites_idx[idx + 1]
            if next_b in d[b].keys():
                surprise.append(log2(1 / d[b][next_b]))

    fig, ax = plt.subplots()
    # ax.set_yscale("log", base=10)
    x = range(0, len(surprise))
    y = surprise
    ax.scatter(x, y, c=y, marker=".", cmap="magma", norm="log")
    plt.show()
    # row_sz = Bytes(16).value
    # for idx in range(row_sz, len(sprites_idx) // 128 + row_sz, row_sz):
    #     s = f"{str(hex(idx - row_sz)).upper()[2:]}"
    #     s += " " * (10 - len(s)) + "| "
    #     for off in range(0, row_sz, 1):
    #         try:
    #             byte = int(sprites_idx[idx + off])
    #             if byte <= 0xF:
    #                 s += f"0{hex(byte).upper()[2:]} "
    #             else:
    #                 s += f"{hex(byte).upper()[2:]} "
    #         except IndexError:
    #             s += ".. "
    #     print(s)

    exit(0)


if __name__ == "__main__":
    main()
