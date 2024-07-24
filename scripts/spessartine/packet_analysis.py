import pathlib

import pyshark
import Levenshtein
import matplotlib.pyplot as plt
import numpy as np
import statistics
import sqlite3
import lzma
import pickle
from sklearn.feature_extraction import DictVectorizer
from sklearn.cluster import MeanShift, estimate_bandwidth
from tqdm import tqdm


if __name__ == "__main__":
    root_path = pathlib.Path(__file__).parent.resolve()
    db_path = root_path / "capture.sqlite3"
    packets = []
    with sqlite3.connect(db_path) as con:
        for capture in tqdm(
            con.execute("""SELECT capture FROM capture""").fetchall(),
            unit=" captures",
            desc="Loading captures",
        ):
            capture = pickle.loads(lzma.decompress(capture[0], format=lzma.FORMAT_XZ))
            for packet in capture:
                packets.append(packet)

    print(f"Loaded {len(packets)} packets.")

    D: list[dict[str, int | float | str]] = [
        {
            "mean_lev_norm_data": statistics.mean(
                [Levenshtein.ratio(p1.DATA.data, p2.DATA.data) for p2 in packets]
            ),
            "ip_src_host": p1.ip.src_host,
            "length": int(p1.length),
        }
        for p1 in packets
    ]
    print(D[0:16])
    v = DictVectorizer(sparse=False)
    X = v.fit_transform(D)

    # centers = [[1, 1], [-1, -1], [1, -1]]
    # X, _ = make_blobs(n_samples=10_000, centers=centers, cluster_std=0.6)
    bw = estimate_bandwidth(X, quantile=0.2, n_samples=500)
    print(f"Estimated bandwidth: {round(bw, 3)}")
    ms = MeanShift(bandwidth=bw, bin_seeding=True)
    ms.fit(X)
    labels = ms.labels_
    cluster_centers = ms.cluster_centers_
    labels_unique = np.unique(labels)
    n_clusters_ = len(labels_unique)
    print(f"# estimated clusters: {n_clusters_}")

    plt.figure(1)
    plt.clf()

    for k in range(n_clusters_):
        my_members = labels == k
        cluster_center = cluster_centers[k]
        plt.plot(X[my_members, 0], X[my_members, 1])
        plt.plot(
            cluster_center[0],
            cluster_center[1],
            markeredgecolor="k",
            markersize=14,
        )
    plt.title("Estimated number of clusters: %d" % n_clusters_)
    plt.show()

    # all_pkts_data = []
    # for pkt in cap:
    #     try:
    #         all_pkts_data.append(pkt.data.data)
    #     except AttributeError:
    #         pass
    #
    # all_to_all_levenshtein_ratio = [
    #     [round(Levenshtein.ratio(s1, s2), 3) for s2 in all_pkts_data]
    #     for s1 in all_pkts_data
    # ]
    # plt.style.use("dark_background")
    # fig, ax = plt.subplots()
    # ax.set(
    #     title="Packet data average normalized indel similarity",
    #     xlabel="Packet index",
    #     ylabel="Normalized indel similarity",
    # )
    # ax.errorbar(
    #     [x for x in range(len(all_to_all_levenshtein_ratio))],
    #     [statistics.mean(l) for l in all_to_all_levenshtein_ratio],
    #     [statistics.variance(l) for l in all_to_all_levenshtein_ratio],
    #     fmt="o",
    # )
    # fig.legend()
    # # ax.set(
    # #     title="Packet data normalized indel similarity",
    # #     xlabel="Packet index",
    # #     ylabel="Packet index",
    # # )
    # # ax.imshow(all_to_all_levenshtein_ratio, norm="logit", interpolation="none")
    # fig.savefig(
    #     "pktanalysis.svg",
    #     dpi=800,
    # )
