# packet_analysis.py

import Levenshtein
import matplotlib.pyplot as plt
import numpy as np
import statistics
import sqlite3
from tqdm import tqdm
from spessartine import unpack
import spessartine


if __name__ == "__main__":
    with sqlite3.connect(spessartine.FilePath.database) as con:
        captures = [
            unpack(row[0], do_decompress=False)
            for row in tqdm(con.execute("SELECT capture FROM capture"))
        ]

    print(len(captures))
