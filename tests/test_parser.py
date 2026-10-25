"""
Test suite for Japanese Financial PDF Parser.
Covers unit tests for value parsing and live sample validation against balance_sheet.pdf.
"""
import pytest
from pathlib import Path

from parser.value_parser import parse_value, normalize_japanese_date
from parser.pipeline import parse_pdf_page


class TestValueParser:
    def test_standard_number_with_commas(self):
        val, is_nil, is_neg, flags = parse_value("2,002,429")
        assert val == 2002429.0
        assert is_nil is False
        assert is_neg is False
        assert flags == []

    def test_white_triangle_negative_marker(self):
        val, is_nil, is_neg, flags = parse_value("△1,923,585")
        assert val == -1923585.0
        assert is_nil is False
        assert is_neg is True

    def test_black_triangle_negative_marker(self):
        val, is_nil, is_neg, flags = parse_value("▲50,000")
        assert val == -50000.0
        assert is_nil is False
        assert is_neg is True

    def test_negative_zero(self):
        val, is_nil, is_neg, flags = parse_value("△0")
        assert val == 0.0
        assert is_nil is False
        assert is_neg is True
        assert "negative_zero" in flags

    def test_nil_markers(self):
        for nil_char in ("－", "—", "−", "\uff0d"):
            val, is_nil, is_neg, flags = parse_value(nil_char)
            assert val is None
            assert is_nil is True

    def test_date_normalization(self):
        raw_dates = [
            ("(2025 年３月 31 日)", "2025-03-31"),
            ("2026年3月31日", "2026-03-31"),
            ("（2024年12月1日）", "2024-12-01"),
        ]
        for raw, expected in raw_dates:
            norm, ok = normalize_japanese_date(raw)
            assert ok is True
            assert norm == expected



class TestLiveSample:
    def test_balance_sheet_sample(self):
        pdf_path = Path("/home/mivikev/Desktop/Dev/UrAI/balance_sheet.pdf")
        assert pdf_path.exists()

        table = parse_pdf_page(str(pdf_path), page_number=1)

        # Structure checks
        assert table.meta["title"] == "連結貸借対照表"
        assert table.meta["unit"] == "千円"
        assert table.meta["n_columns"] == 2
        assert table.meta["n_indent_levels"] == 5
        assert len(table.rows) == 43

        # Token coverage checks
        assert table.audit["coverage_ratio"] == 1.0
        assert len(table.audit["unassigned_tokens"]) == 0
        assert len(table.audit["phantom_tokens"]) == 0

        # Accounting checks
        assert len(table.accounting_checks) == 20
        assert all(c.passed for c in table.accounting_checks)
