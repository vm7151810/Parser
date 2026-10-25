#!/usr/bin/env python3
"""
CLI entry point for Japanese Financial PDF Parser.
Usage:
    python3 main.py balance_sheet.pdf --page 1 --out output/
"""
import argparse
import sys
from pathlib import Path

from parser import parse_pdf_page, render_json, render_markdown, ParserConfig


def main():
    parser = argparse.ArgumentParser(
        description="Convert Japanese financial filing PDF pages into structured tables."
    )
    parser.add_argument("pdf_path", help="Path to input PDF file")
    parser.add_argument("--page", type=int, default=1, help="Page number to parse (1-indexed, default: 1)")
    parser.add_argument("--out", default="output", help="Output directory (default: output/)")
    parser.add_argument("--print-md", action="store_true", help="Print Markdown output to stdout")

    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"Error: File not found: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Parsing {pdf_path.name} (page {args.page})...")
    try:
        table = parse_pdf_page(str(pdf_path), page_number=args.page)
    except Exception as e:
        print(f"Error during parsing: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    stem = pdf_path.stem
    json_path = out_dir / f"{stem}_p{args.page}.json"
    md_path = out_dir / f"{stem}_p{args.page}.md"

    json_str = render_json(table)
    md_str = render_markdown(table)

    json_path.write_text(json_str, encoding="utf-8")
    md_path.write_text(md_str, encoding="utf-8")

    print(f"Successfully parsed page {args.page}!")
    print(f"  • JSON output:     {json_path}")
    print(f"  • Markdown output: {md_path}")
    print("")
    print("--- Summary ---")
    print(f"Title:                 {table.meta.get('title')}")
    print(f"Unit:                  {table.meta.get('unit')}")
    print(f"Rows Extracted:        {len(table.rows)}")
    print(f"Columns Detected:      {table.meta.get('n_columns')}")
    print(f"Indent Levels:         {table.meta.get('n_indent_levels')}")

    audit = table.audit
    print(f"Token Coverage:        {audit.get('coverage_ratio', 0) * 100:.1f}% ({audit.get('total_primary_tokens')} / {audit.get('total_audit_tokens')} tokens)")

    checks = table.accounting_checks
    passed = sum(1 for c in checks if c.passed)
    failed = len(checks) - passed
    rounding = sum(1 for c in checks if c.classification == "source_rounding")
    print(f"Accounting Checks:     {passed} passed ({rounding} with source rounding tolerance), {failed} failed")

    if failed > 0:
        print("\nFailed Checks:")
        for c in checks:
            if not c.passed:
                print(f"  ❌ {c.check_id}: stated={c.stated}, computed={c.computed}, diff={c.diff} (tol=±{c.tolerance})")

    if args.print_md:
        print("\n" + md_str)

    sys.exit(0 if failed == 0 else 2)


if __name__ == "__main__":
    main()
