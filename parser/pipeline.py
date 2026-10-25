"""
Pipeline Coordinator: orchestrates the 12-stage parsing workflow from PDF to ParsedTable.
"""
from __future__ import annotations
import datetime
from pathlib import Path
from typing import Optional
import pdfplumber

from parser.config import ParserConfig
from parser.table_model import ParsedTable
from parser.pdf_extractor import extract_page_tokens
from parser.header_parser import (
    find_header_boundary,
    extract_metadata,
    associate_period_headers
)
from parser.column_detector import detect_columns
from parser.indent_clusterer import cluster_indent_levels
from parser.row_assembler import assemble_rows
from parser.hierarchy_builder import build_hierarchy
from parser.row_typer import type_rows
from parser.consistency import run_accounting_checks
from parser.coverage_auditor import audit_token_coverage


def parse_pdf_page(
    pdf_path: str,
    page_number: int = 1,
    config: Optional[ParserConfig] = None
) -> ParsedTable:
    """
    Parses a single financial statement page from a PDF file.
    """
    if config is None:
        config = ParserConfig()

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    with pdfplumber.open(pdf_path) as pdf:
        if page_number > len(pdf.pages) or page_number < 1:
            raise IndexError(f"Page number {page_number} out of range (PDF has {len(pdf.pages)} pages)")

        page = pdf.pages[page_number - 1]

        # Stage 1: Ingestion, Glyph Metrics, Detached Marker Merging
        tokens, median_glyph_width, thresholds, page_info = extract_page_tokens(
            page, config, page_number
        )

        page_height = page_info["height"]

        # Stage 2: Header Zone Cutoff
        header_y_cutoff = find_header_boundary(
            tokens, page_height, config.header_zone_fallback_fraction
        )
        header_tokens = [t for t in tokens if t["top"] <= header_y_cutoff]

        # Extract statement metadata
        meta = extract_metadata(header_tokens, pdf_file.name, page_number)
        meta["median_glyph_width_pts"] = round(median_glyph_width, 2)
        meta["parsed_at"] = datetime.datetime.now().isoformat()
        warnings: list[str] = []

        # Stage 3: Column Detection via Right-Edge Clustering
        column_centroids = detect_columns(tokens, header_y_cutoff, thresholds)
        if not column_centroids:
            warnings.append("no_financial_columns_detected")

        meta["n_columns"] = len(column_centroids)

        # Stage 4: Period Headers & Date Association
        periods = associate_period_headers(
            header_tokens, column_centroids, thresholds.col_assign
        )
        meta["periods"] = periods
        period_labels = [p["label"] for p in periods]

        # Stage 5: Adaptive Indent Clustering
        first_col_x1 = column_centroids[0] if column_centroids else page_info["width"]
        indent_clusterer = cluster_indent_levels(
            tokens, header_y_cutoff, thresholds, first_col_x1, page_height
        )
        meta["n_indent_levels"] = indent_clusterer.n_levels
        if indent_clusterer.is_flat:
            warnings.append("flat_indentation_detected_using_heuristic_hierarchy")

        # Stage 6: Row Assembly & Nil vs Missing Attribution
        rows = assemble_rows(
            tokens=tokens,
            header_y_cutoff=header_y_cutoff,
            page_height=page_height,
            column_centroids=column_centroids,
            period_labels=period_labels,
            indent_clusterer=indent_clusterer,
            thresholds=thresholds,
            page_number=page_number
        )

        # Stage 7: Indent-Stack Hierarchy & Path Construction
        rows = build_hierarchy(rows, is_flat_indent=indent_clusterer.is_flat)

        # Stage 8 & 9: Label-Stem Triplet Pairing, Row Typing, & Addend Association
        rows = type_rows(rows)

        # Stage 10: Multi-Tier Accounting Consistency Checks
        checks = run_accounting_checks(rows, period_labels)

        # Stage 11: Independent Dual-Engine Coverage Audit
        audit = audit_token_coverage(pdf_path, rows, page_number)

        meta["warnings"] = warnings

        return ParsedTable(
            meta=meta,
            rows=rows,
            accounting_checks=checks,
            audit=audit
        )
