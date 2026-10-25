"""
Coverage Auditor: independently extracts tokens via pdftotext / PyMuPDF
and cross-checks against primary parsed table cells.
"""
from __future__ import annotations
import subprocess
import re
import shutil
from typing import Any
import fitz  # PyMuPDF

from parser.table_model import Row
from parser.value_parser import NIL_CHARS, NEG_PREFIXES

FIN_TOKEN_RE = re.compile(r'[△▲]?\d[\d,]*|[－—−\uff0d―]')
PAGE_NOTE_RE = re.compile(r'^\s*[-－—―]?\s*\d+\s*[-－—―]?\s*$')


def extract_independent_tokens(
    pdf_path: str,
    page_number: int = 1
) -> list[str]:
    """
    Extracts financial tokens from the PDF using pdftotext -layout (or PyMuPDF fallback).
    """
    independent_tokens: list[str] = []

    # 1. Try pdftotext if available
    pdftotext_bin = shutil.which("pdftotext")
    if pdftotext_bin:
        try:
            cmd = [
                pdftotext_bin,
                "-f", str(page_number),
                "-l", str(page_number),
                "-layout",
                pdf_path,
                "-"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            lines = res.stdout.splitlines()

            # Identify data zone: after unit or period headers
            in_data = False
            for line in lines:
                if any(kw in line for kw in ("資産の部", "負債の部", "純資産の部", "流動資産", "固定資産")):
                    in_data = True
                if not in_data:
                    continue
                if PAGE_NOTE_RE.match(line):
                    continue

                for t in FIN_TOKEN_RE.findall(line):
                    t_clean = t.strip()
                    if t_clean in NIL_CHARS or ',' in t_clean or t_clean.startswith(NEG_PREFIXES):
                        independent_tokens.append(t_clean)
            return independent_tokens
        except Exception:
            pass

    # 2. PyMuPDF fallback
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_number - 1]
        text = page.get_text("text")
        lines = text.splitlines()
        in_data = False
        for line in lines:
            if any(kw in line for kw in ("資産の部", "負債の部", "純資産の部", "流動資産", "固定資産")):
                in_data = True
            if not in_data:
                continue
            if PAGE_NOTE_RE.match(line):
                continue

            for t in FIN_TOKEN_RE.findall(line):
                t_clean = t.strip()
                if t_clean in NIL_CHARS or ',' in t_clean or t_clean.startswith(NEG_PREFIXES):
                    independent_tokens.append(t_clean)
    except Exception:
        pass

    return independent_tokens


def audit_token_coverage(
    pdf_path: str,
    rows: list[Row],
    page_number: int = 1
) -> dict[str, Any]:
    """
    Cross-checks primary assigned cell tokens with independent token inventory.
    """
    # Collect all primary assigned non-missing cell raw strings
    primary_tokens: list[str] = []
    for r in rows:
        for v in r.values.values():
            if v.raw and "cell_missing" not in v.flags:
                primary_tokens.append(v.raw.strip())

    audit_tokens = extract_independent_tokens(pdf_path, page_number)

    # Normalize tokens for comparison (NFKC and stripping commas)
    def norm(tok: str) -> str:
        return tok.replace(',', '').replace(' ', '').strip()

    primary_norm = [norm(t) for t in primary_tokens]
    audit_norm = [norm(t) for t in audit_tokens]

    primary_counts: dict[str, int] = {}
    for t in primary_norm:
        primary_counts[t] = primary_counts.get(t, 0) + 1

    audit_counts: dict[str, int] = {}
    for t in audit_norm:
        audit_counts[t] = audit_counts.get(t, 0) + 1

    # Find unassigned tokens (in audit but missing from primary)
    unassigned = []
    for t, cnt in audit_counts.items():
        diff = cnt - primary_counts.get(t, 0)
        if diff > 0:
            unassigned.extend([t] * diff)

    # Find phantom tokens (in primary but missing from audit)
    phantoms = []
    for t, cnt in primary_counts.items():
        diff = cnt - audit_counts.get(t, 0)
        if diff > 0:
            phantoms.extend([t] * diff)

    total_primary = len(primary_tokens)
    total_audit = len(audit_tokens)

    coverage_ratio = round(
        (total_primary / total_audit) if total_audit > 0 else 1.0, 4
    )

    return {
        "total_primary_tokens": total_primary,
        "total_audit_tokens": total_audit,
        "coverage_ratio": coverage_ratio,
        "unassigned_tokens": unassigned,
        "phantom_tokens": phantoms,
    }
