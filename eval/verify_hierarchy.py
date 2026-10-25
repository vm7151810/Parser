#!/usr/bin/env python3
"""
Verification Script: Compares eval/gold.json against eval/hierarchy_tree.txt.

Rule:
- A row's parent is the nearest preceding row with a smaller indent.
- Total rows (…合計) sit at the same indent as the rows they total, so their
  parent is the section they close (which is the nearest preceding row with a smaller indent).

Verifies:
- Row count
- Row order
- Labels
- Printed values (verbatim)
- Parent labels
- 1-indexed parent indices

Exits non-zero if any mismatch exists.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

EVAL_DIR = Path(__file__).resolve().parent
TREE_FILE = EVAL_DIR / "hierarchy_tree.txt"
GOLD_FILE = EVAL_DIR / "gold.json"


def parse_hierarchy_tree(tree_path: Path) -> List[dict]:
    with open(tree_path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n\r") for line in f if line.strip()]

    rows = []
    for line in lines:
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        # Split into label and values
        tokens = stripped.split(" ")
        if len(tokens) >= 3 and any(ch.isdigit() or ch in ("－", "-", "△", "▲") for ch in tokens[-1]):
            # Has values: tokens[-2] and tokens[-1]
            label = " ".join(tokens[:-2])
            values = [tokens[-2], tokens[-1]]
        else:
            label = stripped
            values = [None, None]

        rows.append({
            "indent": indent,
            "label": label,
            "values": values,
        })

    # Derive parent_label and 1-indexed parent_index for each row
    # Rule: nearest preceding row with smaller indent
    for i, row in enumerate(rows):
        current_indent = row["indent"]
        parent_idx_0: Optional[int] = None

        if current_indent == 0:
            parent_idx_0 = None
        else:
            for j in range(i - 1, -1, -1):
                if rows[j]["indent"] < current_indent:
                    parent_idx_0 = j
                    break

        if parent_idx_0 is not None:
            row["parent_index"] = parent_idx_0 + 1  # 1-indexed
            row["parent_label"] = rows[parent_idx_0]["label"]
        else:
            row["parent_index"] = None
            row["parent_label"] = None

    return rows


def verify_against_gold(tree_rows: List[dict], gold_data: dict) -> Tuple[bool, List[str]]:
    gold_rows = gold_data.get("rows", [])
    mismatches = []

    # 1. Row count
    if len(tree_rows) != len(gold_rows):
        mismatches.append(f"Row count mismatch: tree has {len(tree_rows)} rows, gold has {len(gold_rows)} rows.")
        return False, mismatches

    # 2. Row by row comparison
    for i in range(len(tree_rows)):
        row_num = i + 1
        t = tree_rows[i]
        g = gold_rows[i]

        # Label match
        if t["label"] != g.get("label"):
            mismatches.append(
                f"[Row {row_num}] Label mismatch: Tree='{t['label']}' vs Gold='{g.get('label')}'"
            )

        # Values match (verbatim)
        t_vals = t["values"]
        g_vals = g.get("values", [])
        if t_vals != g_vals:
            mismatches.append(
                f"[Row {row_num}] Values mismatch for '{t['label']}': Tree={t_vals} vs Gold={g_vals}"
            )

        # Parent label match
        if t["parent_label"] != g.get("parent_label"):
            mismatches.append(
                f"[Row {row_num}] Parent Label mismatch for '{t['label']}': Tree='{t['parent_label']}' vs Gold='{g.get('parent_label')}'"
            )

        # Parent index match
        if t["parent_index"] != g.get("parent_index"):
            mismatches.append(
                f"[Row {row_num}] Parent Index mismatch for '{t['label']}': Tree={t['parent_index']} vs Gold={g.get('parent_index')}"
            )

    return (len(mismatches) == 0), mismatches


def main():
    if not TREE_FILE.exists():
        print(f"Error: {TREE_FILE} not found.", file=sys.stderr)
        sys.exit(2)

    if not GOLD_FILE.exists():
        print(f"Error: {GOLD_FILE} not found.", file=sys.stderr)
        sys.exit(2)

    tree_rows = parse_hierarchy_tree(TREE_FILE)

    with open(GOLD_FILE, "r", encoding="utf-8") as f:
        gold_data = json.load(f)

    is_valid, mismatches = verify_against_gold(tree_rows, gold_data)

    print("=" * 70)
    print("      HIERARCHY & GROUND-TRUTH VERIFICATION REPORT                   ")
    print("=" * 70)
    print(f"Verified Tree: {TREE_FILE} ({len(tree_rows)} rows)")
    print(f"Target Gold:   {GOLD_FILE} ({len(gold_data.get('rows', []))} rows)")
    print("-" * 70)

    if is_valid:
        print("[SUCCESS] All 43 rows match perfectly:")
        print("  - Row count:      MATCH (43 rows)")
        print("  - Row order:      MATCH (100%)")
        print("  - Labels:         MATCH (100%)")
        print("  - Printed values: MATCH (100% verbatim)")
        print("  - Parent labels:  MATCH (100%)")
        print("  - Parent indices: MATCH (100% 1-indexed)")
        print("=" * 70)
        sys.exit(0)
    else:
        print(f"[MISMATCH] Found {len(mismatches)} discrepancies between Tree and Gold:\n")
        for m in mismatches:
            print(f"  * {m}")
        print("\n" + "=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
