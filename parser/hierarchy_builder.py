"""
Hierarchy Builder: builds unique structural_path for each row
using an indent-stack algorithm.
"""
from __future__ import annotations
import re
from parser.table_model import Row

SECTION_RE = re.compile(r'の部$')
SUBSECTION_RE = re.compile(r'(流動資産|固定資産|有形固定資産|無形固定資産|投資その他の資産|負債|純資産)$')


def build_hierarchy(rows: list[Row], is_flat_indent: bool = False) -> list[Row]:
    """
    Computes structural_path for each row via a LIFO stack.
    If indentation is flat, infers depth heuristically from section/subsection keywords.
    """
    if is_flat_indent:
        # Heuristic level assignment when indent is flat
        for r in rows:
            if SECTION_RE.search(r.label):
                r.level = 0
            elif SUBSECTION_RE.search(r.label) and not r.label.endswith("合計"):
                r.level = 1
            elif r.label.endswith("（純額）") or r.label.endswith("(純額)") or "累計額" in r.label:
                r.level = 3
            elif r.label in ("資産合計", "負債合計", "純資産合計", "負債及び純資産合計"):
                r.level = 0
            elif r.label in ("固定資産合計", "流動負債合計", "固定負債合計"):
                r.level = 1
            elif r.label.endswith("合計"):
                # Subsection total closing the subsection (e.g. 流動資産合計, 有形固定資産合計)
                r.level = 2
            else:
                r.level = 2

    stack: list[tuple[int, str]] = []  # (level, label)
    seen_paths: dict[tuple[str, ...], int] = {}

    for row in rows:
        # Pop stack items that are at the same or deeper level
        while stack and stack[-1][0] >= row.level:
            stack.pop()

        # Build path
        base_path = [s[1] for s in stack] + [row.label]
        path_tuple = tuple(base_path)

        # Disambiguate if collision occurs
        if path_tuple in seen_paths:
            seen_paths[path_tuple] += 1
            count = seen_paths[path_tuple]
            row.flags.append("path_disambiguated")
            row.structural_path = [s[1] for s in stack] + [f"{row.label}#{count}"]
        else:
            seen_paths[path_tuple] = 1
            row.structural_path = base_path

        # Push current row to stack if it can be a parent
        # (Subtotals, nets, and contras don't usually parent other items)
        if not (row.label.endswith("合計") or row.label.endswith("（純額）") or "累計額" in row.label):
            stack.append((row.level, row.label))

    # Derive parent_label and 1-indexed parent_index for each row:
    # Nearest preceding row with a smaller level
    for i, r in enumerate(rows):
        p_idx = None
        p_lbl = None
        if r.level > 0:
            for j in range(i - 1, -1, -1):
                if rows[j].level < r.level:
                    p_idx = j + 1  # 1-indexed
                    p_lbl = rows[j].label
                    break
        r.parent_index = p_idx
        r.parent_label = p_lbl

    return rows
