import sys
from parser import parse_pdf_page

table = parse_pdf_page("balance_sheet.pdf", page_number=1)

imported_eval_or_gold = [
    m for m in sys.modules
    if "eval" in m or "gold" in m
]

print("Imported eval/gold modules:", imported_eval_or_gold)
assert len(imported_eval_or_gold) == 0, f"Found leaked modules: {imported_eval_or_gold}"
print("CONFIRMED: Parser imports nothing from eval or gold.")
