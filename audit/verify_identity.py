import json
import copy
import subprocess

# Read baseline JSON as committed in git
baseline_json_str = subprocess.check_output(["git", "show", "HEAD:output/balance_sheet_p1.json"], text=True)
baseline_dict = json.loads(baseline_json_str)

# Run main.py to generate current output
subprocess.run(["python3", "main.py", "balance_sheet.pdf"], check=True)

with open("output/balance_sheet_p1.json", encoding="utf-8") as f:
    new_dict = json.load(f)

# Compare dictionaries excluding 'parsed_at'
def sanitize(d):
    d = copy.deepcopy(d)
    if "meta" in d and "parsed_at" in d["meta"]:
        del d["meta"]["parsed_at"]
    return d

b_clean = sanitize(baseline_dict)
n_clean = sanitize(new_dict)

diffs = []
if b_clean != n_clean:
    for k in b_clean:
        if b_clean[k] != n_clean.get(k):
            diffs.append(f"Key mismatch '{k}': baseline={b_clean[k]} != new={n_clean.get(k)}")
    for k in n_clean:
        if k not in b_clean:
            diffs.append(f"Extra key in new '{k}'")

print("=== IDENTITY CHECK RESULTS ===")
print(f"Total differences found: {len(diffs)}")
for d in diffs:
    print("  •", d)

if len(diffs) == 0:
    print("VERIFIED: output/balance_sheet_p1.json is 100% IDENTICAL to baseline (excluding meta.parsed_at)!")
else:
    raise AssertionError("Outputs differ!")
