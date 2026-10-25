from parser.pipeline import parse_pdf_page

table = parse_pdf_page("balance_sheet.pdf", page_number=1)
subtotal_rows = [r for r in table.rows if r.row_type == "subtotal"]

print("All Subtotal rows:")
for s in subtotal_rows:
    print(f"  {s.id}: label={s.label}, level={s.level}, path={s.structural_path}")

print("\nExamining composite candidates:")
for sub in subtotal_rows:
    sub_parent = tuple(sub.structural_path[:-1])
    direct_addends = [
        r for r in table.rows
        if r.sum_parent_path == sub_parent and r.row_type in ("item", "net", "contra_standalone")
    ]
    if not direct_addends:
        stem = sub.label.replace("合計", "").strip()
        if stem:
            stem_parent = sub_parent + (stem,)
            direct_addends = [
                r for r in table.rows
                if r.sum_parent_path == stem_parent and r.row_type in ("item", "net", "contra_standalone")
            ]
    print(f"\nSubtotal: {sub.label} (path={sub.structural_path})")
    print(f"  Direct addends count: {len(direct_addends)}")
    if not direct_addends:
        # What are the subtotals under sub_parent or inside this section?
        child_subs = [
            r for r in subtotal_rows
            if r.id != sub.id and r.level > sub.level
        ]
        print(f"  Child subtotals with higher level: {[c.label for c in child_subs]}")
        # For 固定資産合計: level is 2 (wait, what is level of 固定資産合計?)
        print(f"  sub.level: {sub.level}")
