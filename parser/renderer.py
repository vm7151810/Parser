"""
Renderer: outputs ParsedTable to JSON and GitHub Flavored Markdown formats.
"""
from __future__ import annotations
import json
from typing import Any

from parser.table_model import ParsedTable


def render_json(table: ParsedTable, indent: int = 2) -> str:
    """
    Renders ParsedTable as formatted JSON string conforming to schema.
    """
    return json.dumps(table.to_dict(), ensure_ascii=False, indent=indent)


def render_markdown(table: ParsedTable) -> str:
    """
    Renders ParsedTable as a GitHub-flavored Markdown document with
    hierarchical visual indentation, period columns, accounting checks, and audit summary.
    """
    meta = table.meta
    rows = table.rows
    checks = table.accounting_checks
    audit = table.audit

    periods = [p["label"] for p in meta.get("periods", [])]
    if not periods and rows and rows[0].values:
        periods = list(rows[0].values.keys())

    lines: list[str] = []

    # Title & Metadata
    title = meta.get("title", "財務諸表")
    amendment = f" ({meta['amendment']})" if meta.get("amendment") else ""
    lines.append(f"# {title}{amendment}")
    lines.append("")
    lines.append(f"- **Source File**: `{meta.get('source_file')}` (Page {meta.get('page')})")
    lines.append(f"- **Unit (単位)**: `{meta.get('unit', '千円')}`")
    lines.append(f"- **Columns Detected**: {meta.get('n_columns', len(periods))}")
    lines.append(f"- **Hierarchy Levels Detected**: {meta.get('n_indent_levels', 'Adaptive')}")
    lines.append(f"- **Token Coverage Ratio**: `{audit.get('coverage_ratio', 1.0)}` ({audit.get('total_primary_tokens', 0)} / {audit.get('total_audit_tokens', 0)} tokens)")
    lines.append("")

    # Main Financial Statement Table
    lines.append("## Financial Statement Table")
    lines.append("")

    # Table Header
    headers = ["項目 (Line Item)"]
    for p in periods:
        # Check if period has date
        p_obj = next((item for item in meta.get("periods", []) if item["label"] == p), None)
        date_str = f"<br><sub>({p_obj['date']})</sub>" if (p_obj and p_obj.get("date")) else ""
        headers.append(f"{p}{date_str}")
    headers.extend(["Row Type", "Flags"])

    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] + [":---:"] * len(periods) + [":---:", ":---:"]) + " |")

    # Table Rows
    for r in rows:
        # Visual indentation using HTML non-breaking spaces or dashes
        indent_str = "&nbsp;&nbsp;" * r.level
        if r.row_type == "section":
            item_display = f"**{r.label}**"
        elif r.row_type == "subtotal":
            item_display = f"{indent_str}**{r.label}**"
        elif r.row_type in ("header", "gross"):
            item_display = f"{indent_str}*{r.label}*"
        else:
            item_display = f"{indent_str}{r.label}"

        row_cells = [item_display]

        for p in periods:
            cell = r.values.get(p)
            if not cell:
                row_cells.append("-")
            elif cell.nil:
                row_cells.append("－")
            elif cell.numeric is not None:
                flag_mark = " ⚑" if cell.flags else ""
                row_cells.append(f"{cell.raw}{flag_mark}")
            elif "cell_missing" in cell.flags:
                row_cells.append("*missing* ⚑")
            else:
                row_cells.append(cell.raw or "-")

        row_cells.append(f"`{r.row_type}`")
        flag_str = ", ".join(r.flags) if r.flags else "—"
        row_cells.append(flag_str)

        lines.append("| " + " | ".join(row_cells) + " |")

    lines.append("")

    # Accounting Consistency Checks Table
    lines.append("## Accounting Consistency Checks")
    lines.append("")
    if checks:
        lines.append("| Check ID | Type | Period | Computed | Stated | Diff | Tol | Status | Notes |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |")
        for c in checks:
            status_icon = "✅ PASS" if c.passed else "❌ FAIL"
            cls_badge = f"`{c.classification}`"
            computed_str = f"{c.computed:,.0f}" if c.computed is not None else "-"
            stated_str = f"{c.stated:,.0f}" if c.stated is not None else "-"
            diff_str = f"{c.diff:,.0f}" if c.diff is not None else "-"

            lines.append(
                f"| `{c.check_id}` | {c.check_type} | {c.period} | "
                f"{computed_str} | {stated_str} | {diff_str} | ±{c.tolerance} | "
                f"{status_icon} ({cls_badge}) | {c.notes} |"
            )
    else:
        lines.append("No accounting checks were evaluated.")

    lines.append("")

    # Audit & Provenance Notes
    lines.append("## Audit & Quality Assurance")
    lines.append("")
    lines.append(f"- **Independent Audit Discrepancies**: {len(audit.get('unassigned_tokens', []))} unassigned, {len(audit.get('phantom_tokens', []))} phantom.")
    if audit.get("unassigned_tokens"):
        lines.append(f"  - Unassigned tokens: `{audit['unassigned_tokens']}`")
    if audit.get("phantom_tokens"):
        lines.append(f"  - Phantom tokens: `{audit['phantom_tokens']}`")
    lines.append("- **Notes**: `⚑` marks cells with uncertainty, missing values, or negative zero flags.")
    lines.append("")

    return "\n".join(lines)
