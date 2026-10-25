"""
ParserConfig: all spatial thresholds in glyph-widths (converted to pts at runtime).
ScaledThresholds: the runtime pt values derived from median glyph width.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class ParserConfig:
    # Spatial thresholds (in multiples of median glyph width)
    indent_gap_glyphs: float = 0.5    # max intra-cluster variation between x0 of same indent level
    col_x1_gap_glyphs: float = 3.0    # min gap between numeric columns
    col_assign_glyphs: float = 2.0    # column assignment x1 tolerance

    # Absolute thresholds (pts) — glyph-size scaling is less meaningful here
    y_band_tol_pts: float = 2.0      # y-overlap tolerance for same-row grouping
    detach_merge_y_tol_pts: float = 2.0  # y-overlap for detached △ merging

    # Accounting
    rounding_per_term: float = 0.5   # max rounding error per addend (source unit)
    suspect_multiplier: float = 10.0  # diff > suspect * tolerance → parse_error

    # Header zone fallback (fraction of page height)
    header_zone_fallback_fraction: float = 0.15

    def scale(self, median_glyph_width: float) -> ScaledThresholds:
        return ScaledThresholds(
            indent_gap=self.indent_gap_glyphs * median_glyph_width,
            col_x1_gap=self.col_x1_gap_glyphs * median_glyph_width,
            col_assign=self.col_assign_glyphs * median_glyph_width,
            y_band_tol=self.y_band_tol_pts,
            detach_merge_y_tol=self.detach_merge_y_tol_pts,
        )


@dataclass
class ScaledThresholds:
    indent_gap: float
    col_x1_gap: float
    col_assign: float
    y_band_tol: float
    detach_merge_y_tol: float
