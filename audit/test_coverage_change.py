import shutil
import subprocess
import fitz
import re
from parser.pipeline import parse_pdf_page
from parser.value_parser import NIL_CHARS, NEG_PREFIXES

FIN_TOKEN_RE = re.compile(r'[△▲]?\d[\d,]*|[－—−\uff0d―]')
PAGE_NOTE_RE = re.compile(r'^\s*[-－—―]?\s*\d+\s*[-－—―]?\s*$')

def test_audit(first_row_label):
    pdftotext_bin = shutil.which("pdftotext")
    cmd = [pdftotext_bin, "-f", "1", "-l", "1", "-layout", "balance_sheet.pdf", "-"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    lines = res.stdout.splitlines()
    tokens = []
    in_data = False
    for line in lines:
        if first_row_label in line:
            in_data = True
        if not in_data:
            continue
        if PAGE_NOTE_RE.match(line):
            continue
        for t in FIN_TOKEN_RE.findall(line):
            t_clean = t.strip()
            if t_clean in NIL_CHARS or ',' in t_clean or t_clean.startswith(NEG_PREFIXES):
                tokens.append(t_clean)
    return tokens

table = parse_pdf_page("balance_sheet.pdf", page_number=1)
first_label = table.rows[0].label
tokens = test_audit(first_label)
print(f"First row label: {first_label}")
print(f"Extracted independent tokens count: {len(tokens)}")
baseline_audit_tokens = table.audit["total_audit_tokens"]
print(f"Baseline audit tokens count: {baseline_audit_tokens}")
assert len(tokens) == baseline_audit_tokens
print("Tokens match baseline exactly!")
