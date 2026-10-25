"""
Indent Clusterer: clusters label left-edges (x0) to adaptively infer
hierarchy depth levels without hardcoded coordinates.
"""
from __future__ import annotations
import statistics
from typing import Any

from parser.config import ScaledThresholds
from parser.column_detector import is_financial_token


class IndentClusterer:
    def __init__(
        self,
        clusters: list[list[float]],
        centroids: dict[int, float],
        is_flat: bool
    ):
        self.clusters = clusters
        self.centroids = centroids
        self.is_flat = is_flat
        self.n_levels = len(centroids)

    def get_level(self, x0: float) -> tuple[int, bool]:
        """
        Maps an x0 coordinate to the nearest indent level.
        Returns: (level_int, is_uncertain)
        """
        if self.is_flat or not self.centroids:
            return 0, False

        # Find closest centroid
        best_level = 0
        min_dist = float("inf")
        for lvl, c_x0 in self.centroids.items():
            dist = abs(x0 - c_x0)
            if dist < min_dist:
                min_dist = dist
                best_level = lvl

        # If it falls far from the cluster centroid (> 4 pt), mark as uncertain
        is_uncertain = min_dist > 4.0
        return best_level, is_uncertain


def cluster_indent_levels(
    tokens: list[dict[str, Any]],
    header_y_cutoff: float,
    thresholds: ScaledThresholds,
    first_col_x1: float,
    page_height: float = 1000.0
) -> IndentClusterer:
    """
    Collects label x0 values in the data zone and clusters them into discrete indent levels.
    """
    label_x0s = []

    for t in tokens:
        # Must be in data zone, situated to the left of the financial columns, and not financial
        if t["top"] > header_y_cutoff and t["x1"] < first_col_x1:
            if t["top"] > page_height * 0.88 or t.get("text", "").strip() in ('-', '―', 'ー', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'):
                if t["top"] > page_height * 0.75:
                    continue
            text = t.get("text", "").strip()
            if text and not is_financial_token(text):
                label_x0s.append(round(t["x0"], 2))

    if not label_x0s:
        return IndentClusterer([], {}, is_flat=True)

    unique_x0s = sorted(set(label_x0s))

    # Cluster with gap threshold
    clusters: list[list[float]] = [[unique_x0s[0]]]
    for x0 in unique_x0s[1:]:
        if x0 - clusters[-1][-1] <= thresholds.indent_gap:
            clusters[-1].append(x0)
        else:
            clusters.append([x0])

    is_flat = len(clusters) < 2

    # Map each cluster to a centroid
    centroids: dict[int, float] = {}
    for idx, c in enumerate(clusters):
        min_c, max_c = min(c), max(c)
        pts = [x for x in label_x0s if min_c <= x <= max_c]
        centroids[idx] = round(statistics.median(pts), 2)

    return IndentClusterer(clusters, centroids, is_flat)
