"""
Data model for the parser output.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class Provenance:
    page: int
    x0: float
    y0: float
    x1: float
    y1: float
    token_index: Optional[int] = None

    def to_dict(self) -> dict:
        d = {"page": self.page, "x0": round(self.x0, 2), "y0": round(self.y0, 2),
             "x1": round(self.x1, 2), "y1": round(self.y1, 2)}
        if self.token_index is not None:
            d["token_index"] = self.token_index
        return d


@dataclass
class CellValue:
    raw: str                       # original string from PDF
    numeric: Optional[float]       # parsed number, None for nil or parse failure
    nil: bool                      # explicit nil marker present (－ etc.)
    negative: bool                 # △/▲ prefix was present
    flags: list[str] = field(default_factory=list)
    provenance: Optional[Provenance] = None

    def to_dict(self) -> dict:
        d = {
            "raw": self.raw,
            "numeric": self.numeric,
            "nil": self.nil,
            "negative": self.negative,
            "flags": self.flags,
        }
        if self.provenance:
            d["provenance"] = self.provenance.to_dict()
        return d


@dataclass
class Row:
    id: str
    structural_path: list[str]     # indent-stack path; unique; used as eval key
    label: str
    level: int
    row_type: str   # section|header|item|gross|contra|contra_standalone|net|net_orphan|subtotal
    gross_parent: Optional[str]    # label of the paired gross row (for contra/net)
    block_id: Optional[str]        # shared by all rows in a gross/contra/net triplet
    sum_parent_path: Optional[tuple]  # tuple for hashing; used in addend lookup
    values: dict[str, CellValue]   # period_label → CellValue
    provenance_label: Optional[Provenance]
    parent_index: Optional[int] = None
    parent_label: Optional[str] = None
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        values_list = []
        for v in self.values.values():
            if v.nil or v.numeric is not None:
                values_list.append(v.raw)
            else:
                values_list.append(None)

        return {
            "id": self.id,
            "structural_path": self.structural_path,
            "label": self.label,
            "level": self.level,
            "parent_index": self.parent_index,
            "parent_label": self.parent_label,
            "row_type": self.row_type,
            "gross_parent": self.gross_parent,
            "block_id": self.block_id,
            "sum_parent_path": list(self.sum_parent_path) if self.sum_parent_path else None,
            "values": values_list,
            "cells": {k: v.to_dict() for k, v in self.values.items()},
            "provenance_label": self.provenance_label.to_dict() if self.provenance_label else None,
            "flags": self.flags,
        }


@dataclass
class AccountingCheck:
    check_id: str
    check_type: str   # subtotal | net_value | grand_total
    period: str
    stated_path: list[str]
    n_terms: int
    tolerance: int
    addend_paths: list[list[str]]
    computed: Optional[float]
    stated: Optional[float]
    diff: Optional[float]
    classification: str  # exact|source_rounding|suspect|parse_error|skip
    passed: bool
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "check_type": self.check_type,
            "period": self.period,
            "stated_path": self.stated_path,
            "n_terms": self.n_terms,
            "tolerance": self.tolerance,
            "addend_paths": self.addend_paths,
            "computed": self.computed,
            "stated": self.stated,
            "diff": self.diff,
            "classification": self.classification,
            "passed": self.passed,
            "notes": self.notes,
        }


@dataclass
class ParsedTable:
    meta: dict
    rows: list[Row]
    accounting_checks: list[AccountingCheck]
    audit: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        headers = [
            p["label"] + (f" ({p['date']})" if p.get("date") else "")
            for p in self.meta.get("periods", [])
        ]
        return {
            "column_headers": headers,
            "meta": self.meta,
            "rows": [r.to_dict() for r in self.rows],
            "accounting_checks": [c.to_dict() for c in self.accounting_checks],
            "audit": self.audit,
        }

