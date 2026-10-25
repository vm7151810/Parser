import json
import copy
from parser.pipeline import parse_pdf_page
import parser.coverage_auditor as coverage_auditor
import parser.pipeline as pipeline

with open("output/balance_sheet_p1.json", encoding="utf-8") as f:
    baseline_json = json.load(f)

# Test with dynamic start labels derived from rows (level 0 sections)
orig_audit = pipeline.audit_token_coverage

def audit_token_coverage_agnostic(pdf_path, rows, page_number=1):
    section_labels = tuple(r.label for r in rows if r.level == 0)
    # If no level 0 section, use first row label
    if not section_labels and rows:
        section_labels = (rows[0].label,)
        
    primary_tokens = []
    for r in rows:
        for v in r.values.values():
            if v.raw and "cell_missing" not in v.flags:
                primary_tokens.append(v.raw.strip())

    import shutil, subprocess, fitz
    from parser.value_parser import NIL_CHARS, NEG_PREFIXES
    import re
    FIN_TOKEN_RE = re.compile(r'[△▲]?\d[\d,]*|[－—−\uff0d―]')
    PAGE_NOTE_RE = re.compile(r'^\s*[-－—―]?\s*\d+\s*[-－—―]?\s*$')
    
    independent_tokens = []
    pdftotext_bin = shutil.which("pdftotext")
    if pdftotext_bin:
        try:
            cmd = [pdftotext_bin, "-f", str(page_number), "-l", str(page_number), "-layout", pdf_path, "-"]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            in_data = False
            for line in res.stdout.splitlines():
                if any(lbl in line for lbl in section_labels):
                    in_data = True
                if not in_data or PAGE_NOTE_RE.match(line):
                    continue
                for t in FIN_TOKEN_RE.findall(line):
                    t_clean = t.strip()
                    if t_clean in NIL_CHARS or ',' in t_clean or t_clean.startswith(NEG_PREFIXES):
                        independent_tokens.append(t_clean)
        except Exception:
            pass
            
    def norm(tok: str) -> str:
        return tok.replace(',', '').replace(' ', '').strip()

    primary_norm = [norm(t) for t in primary_tokens]
    audit_norm = [norm(t) for t in independent_tokens]

    primary_counts = {}
    for t in primary_norm:
        primary_counts[t] = primary_counts.get(t, 0) + 1
    audit_counts = {}
    for t in audit_norm:
        audit_counts[t] = audit_counts.get(t, 0) + 1

    unassigned = []
    for t, cnt in audit_counts.items():
        diff = cnt - primary_counts.get(t, 0)
        if diff > 0:
            unassigned.extend([t] * diff)

    phantoms = []
    for t, cnt in primary_counts.items():
        diff = cnt - audit_counts.get(t, 0)
        if diff > 0:
            phantoms.extend([t] * diff)

    tot_p = len(primary_tokens)
    tot_a = len(independent_tokens)
    return {
        "total_primary_tokens": tot_p,
        "total_audit_tokens": tot_a,
        "coverage_ratio": round((tot_p / tot_a) if tot_a > 0 else 1.0, 4),
        "unassigned_tokens": unassigned,
        "phantom_tokens": phantoms,
    }

pipeline.audit_token_coverage = audit_token_coverage_agnostic
new_table = parse_pdf_page("balance_sheet.pdf", page_number=1)
pipeline.audit_token_coverage = orig_audit
new_json = new_table.to_dict()

b_clean = copy.deepcopy(baseline_json)
n_clean = copy.deepcopy(new_json)
del b_clean["meta"]["parsed_at"]
del n_clean["meta"]["parsed_at"]

diffs = []
for k in b_clean:
    if b_clean[k] != n_clean[k]:
        diffs.append(f"Difference in {k}")
print("Differences with dynamic coverage auditor:", len(diffs))
assert len(diffs) == 0
print("CONFIRMED: Output JSON is identical!")
