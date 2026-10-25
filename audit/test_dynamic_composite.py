from parser.pipeline import parse_pdf_page
import copy

table = parse_pdf_page("balance_sheet.pdf", page_number=1)
subtotal_rows = [r for r in table.rows if r.row_type == "subtotal"]

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
            
    if not direct_addends:
        # Dynamic discovery: child subtotals under sub_parent at immediate subordinate level
        candidates = [
            r for r in subtotal_rows
            if r.id != sub.id
            and len(r.structural_path) > len(sub_parent)
            and tuple(r.structural_path[:len(sub_parent)]) == sub_parent
        ]
        # Group by level and take the level closest to sub.level (immediate child level)
        child_levels = sorted(set(r.level for r in candidates if r.level > sub.level))
        if child_levels:
            target_level = child_levels[0] # immediate subordinate level
            dynamic_addends = [r for r in candidates if r.level == target_level]
        else:
            dynamic_addends = []
            
        print(f"Subtotal: {sub.label} (level {sub.level}, parent={sub_parent})")
        print(f"  Dynamically discovered addends: {[a.label for a in dynamic_addends]}")
