#!/usr/bin/env python3
"""
Fault-Injection Test Suite for Japanese Table Parser Evaluation Harness.

Tests:
1. Gold vs. Gold (Expect 0 discrepancies, PASS, exit 0)
2. Drop middle row (R8:row missing_row CRITICAL, subsumed_cells=2, orphaned_children=[])
3. Duplicate row (EXTRA:P6 extra_row CRITICAL)
4. Swap columns (72 wrong_printed_value entries on differing value cells)
5. "△0" -> "0" (R12:C2 sign_error ERROR, numeric_match=True)
6. "－" -> "0" (R26:C1 nil_zero ERROR, numeric_match=False)
7. "－" -> null (R26:C1 nil_missing ERROR, numeric_match=False)
8. Remove △ from contra (R17:C1 sign_error ERROR, numeric_match=False; no accounting entry in ledger)
9. Wrong label with matching values (R5:label wrong_label ERROR; hierarchy still checked)
10. Wrong metadata unit (META:unit wrong_metadata CRITICAL)
11. Wrong metadata column count (META:columns wrong_metadata CRITICAL)
12. Duplicate row tie-breaking (earlier matches, later is extra)
13. Drop row 1 no cascade (R1:row missing_row CRITICAL, subsumed_cells=2, orphaned_children=[2, 14, 43])
14. Waiver applies (matching id, type, actual -> waived=True, exit 0)
15. Waiver fails when actual changed (actual changed -> waived=False, exit 1)
16. Malformed waiver file -> exit 2
17. Malformed parser input file -> exit 2
18. Stale waiver listed as non-gating warning
"""

from __future__ import annotations
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest

from evaluate import evaluate_table

GOLD_PATH = Path(__file__).resolve().parent / "gold.json"
EVALUATE_PY = Path(__file__).resolve().parent / "evaluate.py"


@pytest.fixture
def gold_data() -> dict:
    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# =====================================================================
# 1. Gold vs. Gold Self-Evaluation
# =====================================================================
def test_01_gold_vs_gold_self_eval(gold_data):
    """Test 1: Gold compared to itself must produce an empty ledger and exit code 0."""
    # PREDICTION:
    # - ledger: []
    # - exit_code: 0
    # - rates: all 1.0 (100%)
    report = evaluate_table(gold_data, gold_data)
    assert report["ledger"] == [], f"Expected empty ledger, got: {report['ledger']}"
    assert report["exit_code"] == 0
    assert report["status"] == "PASS"
    assert report["rates"]["row_f1"] == 1.0
    assert report["rates"]["hierarchy_accuracy"] == 1.0
    assert report["rates"]["value_cell_exact_accuracy"] == 1.0
    assert report["diagnostics"]["failed_checks"] == 0


# =====================================================================
# 2. Drop Middle Row
# =====================================================================
def test_02_fault_drop_middle_row(gold_data):
    """Test 2: Drop row 8 (仕掛品). Expect exactly 1 missing_row entry with subsumed_cells=2."""
    # PREDICTION:
    # - ledger: exactly 1 entry
    #   - id: "R8:row"
    #   - type: "missing_row"
    #   - severity: "CRITICAL"
    #   - expected: {"row_index": 8, "label": "仕掛品"}
    #   - actual: None
    #   - detail: {"subsumed_cells": 2, "orphaned_children": []}
    # - exit_code: 1
    perturbed = copy.deepcopy(gold_data)
    dropped_row = perturbed["rows"].pop(7)  # 0-indexed 7 is row_index 8
    assert dropped_row["label"] == "仕掛品"

    report = evaluate_table(gold_data, perturbed)
    ledger = report["ledger"]
    assert len(ledger) == 1, f"Expected 1 ledger entry, got {len(ledger)}: {ledger}"
    entry = ledger[0]
    assert entry["id"] == "R8:row"
    assert entry["type"] == "missing_row"
    assert entry["severity"] == "CRITICAL"
    assert entry["expected"]["row_index"] == 8
    assert entry["expected"]["label"] == "仕掛品"
    assert entry["actual"] is None
    assert entry["detail"]["subsumed_cells"] == 2
    assert entry["detail"]["orphaned_children"] == []
    assert not entry["waived"]
    assert report["exit_code"] == 1


# =====================================================================
# 3. Duplicate Row
# =====================================================================
def test_03_fault_duplicate_row(gold_data):
    """Test 3: Duplicate row 5 (売掛金). Expect exactly 1 extra_row entry for EXTRA:P6."""
    # PREDICTION:
    # - ledger: exactly 1 entry
    #   - id: "EXTRA:P6"
    #   - type: "extra_row"
    #   - severity: "CRITICAL"
    #   - expected: None
    #   - actual: {"parser_row_index": 6, "label": "売掛金"}
    #   - detail: {}
    # - exit_code: 1
    perturbed = copy.deepcopy(gold_data)
    dup_row = copy.deepcopy(perturbed["rows"][4])  # row_index 5
    assert dup_row["label"] == "売掛金"
    perturbed["rows"].insert(5, dup_row)

    report = evaluate_table(gold_data, perturbed)
    ledger = report["ledger"]
    assert len(ledger) == 1, f"Expected 1 ledger entry, got {len(ledger)}: {ledger}"
    entry = ledger[0]
    assert entry["id"] == "EXTRA:P6"
    assert entry["type"] == "extra_row"
    assert entry["severity"] == "CRITICAL"
    assert entry["expected"] is None
    assert entry["actual"]["parser_row_index"] == 6
    assert entry["actual"]["label"] == "売掛金"
    assert report["exit_code"] == 1


# =====================================================================
# 4. Swap Columns
# =====================================================================
def test_04_fault_swap_columns(gold_data):
    """Test 4: Swap Col 1 and Col 2. Expect 72 wrong_printed_value entries (36 rows x 2 cols)."""
    # PREDICTION:
    # - 36 rows have differing Col 1 and Col 2 values in gold.json (Row 37 has identical [1123, 1123])
    # - 36 * 2 = 72 value cell discrepancies, all type "wrong_printed_value", severity "ERROR"
    # - exit_code: 1
    perturbed = copy.deepcopy(gold_data)
    for r in perturbed["rows"]:
        vals = r.get("values", [])
        if len(vals) == 2 and vals[0] is not None:
            r["values"] = [vals[1], vals[0]]

    report = evaluate_table(gold_data, perturbed)
    ledger = report["ledger"]
    assert len(ledger) == 72, f"Expected 72 entries, got {len(ledger)}"
    for entry in ledger:
        assert entry["type"] == "wrong_printed_value"
        assert entry["severity"] == "ERROR"
        assert "numeric_match" in entry["detail"]
    assert report["exit_code"] == 1


# =====================================================================
# 5. "△0" -> "0"
# =====================================================================
def test_05_fault_negative_zero_marker(gold_data):
    """Test 5: '△0' -> '0' in 貸倒引当金 Col 2. Expect exactly 1 sign_error entry."""
    # PREDICTION:
    # - ledger: exactly 1 entry
    #   - id: "R12:C2"
    #   - type: "sign_error"
    #   - severity: "ERROR"
    #   - expected: "△0"
    #   - actual: "0"
    #   - detail: {"numeric_match": True}
    # - exit_code: 1
    perturbed = copy.deepcopy(gold_data)
    assert perturbed["rows"][11]["label"] == "貸倒引当金"
    perturbed["rows"][11]["values"][1] = "0"

    report = evaluate_table(gold_data, perturbed)
    ledger = report["ledger"]
    assert len(ledger) == 1, f"Expected 1 entry, got {len(ledger)}: {ledger}"
    entry = ledger[0]
    assert entry["id"] == "R12:C2"
    assert entry["type"] == "sign_error"
    assert entry["severity"] == "ERROR"
    assert entry["expected"] == "△0"
    assert entry["actual"] == "0"
    assert entry["detail"].get("numeric_match") is True
    assert report["exit_code"] == 1


# =====================================================================
# 6. "－" -> "0"
# =====================================================================
def test_06_fault_nil_to_zero(gold_data):
    """Test 6: '－' -> '0' in 建設仮勘定 Col 1. Expect exactly 1 nil_zero entry."""
    # PREDICTION:
    # - ledger: exactly 1 entry
    #   - id: "R26:C1"
    #   - type: "nil_zero"
    #   - severity: "ERROR"
    #   - expected: "－"
    #   - actual: "0"
    #   - detail: {"numeric_match": False}
    # - exit_code: 1
    perturbed = copy.deepcopy(gold_data)
    assert perturbed["rows"][25]["label"] == "建設仮勘定"
    perturbed["rows"][25]["values"][0] = "0"

    report = evaluate_table(gold_data, perturbed)
    ledger = report["ledger"]
    assert len(ledger) == 1, f"Expected 1 entry, got {len(ledger)}: {ledger}"
    entry = ledger[0]
    assert entry["id"] == "R26:C1"
    assert entry["type"] == "nil_zero"
    assert entry["severity"] == "ERROR"
    assert entry["expected"] == "－"
    assert entry["actual"] == "0"
    assert report["exit_code"] == 1


# =====================================================================
# 7. "－" -> null
# =====================================================================
def test_07_fault_nil_to_null(gold_data):
    """Test 7: '－' -> null in 建設仮勘定 Col 1. Expect exactly 1 nil_missing entry."""
    # PREDICTION:
    # - ledger: exactly 1 entry
    #   - id: "R26:C1"
    #   - type: "nil_missing"
    #   - severity: "ERROR"
    #   - expected: "－"
    #   - actual: None
    #   - detail: {"numeric_match": False}
    # - exit_code: 1
    perturbed = copy.deepcopy(gold_data)
    assert perturbed["rows"][25]["label"] == "建設仮勘定"
    perturbed["rows"][25]["values"][0] = None

    report = evaluate_table(gold_data, perturbed)
    ledger = report["ledger"]
    assert len(ledger) == 1, f"Expected 1 entry, got {len(ledger)}: {ledger}"
    entry = ledger[0]
    assert entry["id"] == "R26:C1"
    assert entry["type"] == "nil_missing"
    assert entry["severity"] == "ERROR"
    assert entry["expected"] == "－"
    assert entry["actual"] is None
    assert report["exit_code"] == 1


# =====================================================================
# 8. Remove △ from Contra Value
# =====================================================================
def test_08_fault_remove_delta_contra(gold_data):
    """Test 8: Remove △ from Row 17 Col 1 (減価償却累計額). Expect exactly 1 sign_error entry."""
    # PREDICTION:
    # - ledger: exactly 1 entry
    #   - id: "R17:C1"
    #   - type: "sign_error"
    #   - severity: "ERROR"
    #   - expected: "△1,923,585"
    #   - actual: "1,923,585"
    #   - detail: {"numeric_match": False}
    # - Collateral: net_buildings accounting check fails in diagnostics section, but produces NO ledger entry
    # - exit_code: 1
    perturbed = copy.deepcopy(gold_data)
    assert perturbed["rows"][16]["label"] == "減価償却累計額"
    perturbed["rows"][16]["values"][0] = "1,923,585"

    report = evaluate_table(gold_data, perturbed)
    ledger = report["ledger"]
    assert len(ledger) == 1, f"Expected 1 entry, got {len(ledger)}: {ledger}"
    entry = ledger[0]
    assert entry["id"] == "R17:C1"
    assert entry["type"] == "sign_error"
    assert entry["severity"] == "ERROR"
    assert entry["expected"] == "△1,923,585"
    assert entry["actual"] == "1,923,585"
    assert entry["detail"].get("numeric_match") is False
    assert report["exit_code"] == 1

    # Diagnostics check still catches it, but does not enter the ledger
    net_building_check = next(c for c in report["diagnostics"]["details"] if c["check_id"] == "net_buildings" and "2025" in c["column"])
    assert not net_building_check["passed"]


# =====================================================================
# 9. Wrong Label (Gap Pairing by Identical Value Tuple)
# =====================================================================
def test_09_fault_wrong_label(gold_data):
    """Test 9: Change label of row 5 (売掛金 -> 売掛金_modified), keep values identical.
    Expects gap pairing: exactly 1 wrong_label entry (R5:label), hierarchy still checked."""
    # PREDICTION:
    # - Anchors align row 4 and row 6.
    # - Gap has Gold row 5 and Parser row 5 with identical values ["2,019,476", "884,339"].
    # - Pairs row 5: emits 1 entry R5:label (wrong_label, ERROR).
    # - Hierarchy matches gold parent (流動資産) -> 0 wrong_parent entries.
    # - Cell values match -> 0 cell entries.
    # - Total ledger entries: 1
    # - exit_code: 1
    perturbed = copy.deepcopy(gold_data)
    assert perturbed["rows"][4]["label"] == "売掛金"
    perturbed["rows"][4]["label"] = "売掛金_modified"

    report = evaluate_table(gold_data, perturbed)
    ledger = report["ledger"]
    assert len(ledger) == 1, f"Expected 1 entry, got {len(ledger)}: {ledger}"
    entry = ledger[0]
    assert entry["id"] == "R5:label"
    assert entry["type"] == "wrong_label"
    assert entry["severity"] == "ERROR"
    assert entry["expected"] == "売掛金"
    assert entry["actual"] == "売掛金_modified"
    assert report["exit_code"] == 1


# =====================================================================
# 10. Wrong Metadata Unit
# =====================================================================
def test_10_fault_wrong_metadata_unit(gold_data):
    """Test 10: Change unit from 千円 to 百万円. Expect META:unit wrong_metadata CRITICAL."""
    # PREDICTION:
    # - ledger: exactly 1 entry
    #   - id: "META:unit"
    #   - type: "wrong_metadata"
    #   - severity: "CRITICAL"
    #   - expected: "千円"
    #   - actual: "百万円"
    # - exit_code: 1
    perturbed = copy.deepcopy(gold_data)
    perturbed["metadata"]["unit"] = "百万円"

    report = evaluate_table(gold_data, perturbed)
    ledger = report["ledger"]
    assert len(ledger) == 1, f"Expected 1 entry, got {len(ledger)}: {ledger}"
    entry = ledger[0]
    assert entry["id"] == "META:unit"
    assert entry["type"] == "wrong_metadata"
    assert entry["severity"] == "CRITICAL"
    assert entry["expected"] == "千円"
    assert entry["actual"] == "百万円"
    assert report["exit_code"] == 1


# =====================================================================
# 11. Wrong Metadata Column Count
# =====================================================================
def test_11_fault_wrong_metadata_columns(gold_data):
    """Test 11: Add a 3rd column to metadata headers and parser rows.
    Expect META:columns wrong_metadata CRITICAL, cell comparisons limited to first 2 cols."""
    # PREDICTION:
    # - ledger: exactly 1 entry
    #   - id: "META:columns"
    #   - type: "wrong_metadata"
    #   - severity: "CRITICAL"
    #   - expected: 2
    #   - actual: 3
    #   - detail: {"gold_columns": [...], "parser_columns": [...], "ignored_columns": [3]}
    # - No cell discrepancies on first 2 columns because they match gold.
    # - exit_code: 1
    perturbed = copy.deepcopy(gold_data)
    perturbed["metadata"]["column_headers"].append("余分な列 (2027年３月31日)")
    for r in perturbed["rows"]:
        vals = r.get("values", [])
        if vals is not None:
            vals.append("999,999" if vals[0] is not None else None)

    report = evaluate_table(gold_data, perturbed)
    ledger = report["ledger"]
    assert len(ledger) == 1, f"Expected 1 entry, got {len(ledger)}: {ledger}"
    entry = ledger[0]
    assert entry["id"] == "META:columns"
    assert entry["type"] == "wrong_metadata"
    assert entry["severity"] == "CRITICAL"
    assert entry["expected"] == 2
    assert entry["actual"] == 3
    assert entry["detail"]["ignored_columns"] == [3]
    assert report["exit_code"] == 1


# =====================================================================
# 12. Duplicate Row Tie-Break
# =====================================================================
def test_12_duplicate_row_tie_break(gold_data):
    """Test 12: Verify deterministic alignment tie-breaking:
    When row 5 is duplicated, parser row 5 matches gold row 5, and parser row 6 is extra."""
    # PREDICTION:
    # - Gold row 5 aligns to Parser row 5 (0-indexed 4 -> 4)
    # - Parser row 6 is extra -> EXTRA:P6
    perturbed = copy.deepcopy(gold_data)
    dup_row = copy.deepcopy(perturbed["rows"][4])
    perturbed["rows"].insert(5, dup_row)

    report = evaluate_table(gold_data, perturbed)
    ledger = report["ledger"]
    assert len(ledger) == 1
    assert ledger[0]["id"] == "EXTRA:P6"
    assert ledger[0]["actual"]["parser_row_index"] == 6


# =====================================================================
# 13. Drop Row 1 No Cascade
# =====================================================================
def test_13_fault_drop_row_1_no_cascade(gold_data):
    """Test 13: Drop Row 1 (資産の部).
    Expects exactly ONE entry: R1:row (missing_row, CRITICAL),
    with subsumed_cells=2 and orphaned_children=[2, 14, 43].
    Rows 2, 14, 43 must NOT emit wrong_parent."""
    # PREDICTION:
    # - ledger: exactly 1 entry
    #   - id: "R1:row"
    #   - type: "missing_row"
    #   - severity: "CRITICAL"
    #   - expected: {"row_index": 1, "label": "資産の部"}
    #   - actual: None
    #   - detail: {"subsumed_cells": 2, "orphaned_children": [2, 14, 43]}
    # - Rows 2, 14, 43 do NOT emit wrong_parent because their gold parent is missing
    # - exit_code: 1
    perturbed = copy.deepcopy(gold_data)
    dropped = perturbed["rows"].pop(0)
    assert dropped["label"] == "資産の部"

    report = evaluate_table(gold_data, perturbed)
    ledger = report["ledger"]
    assert len(ledger) == 1, f"Expected 1 entry, got {len(ledger)}: {ledger}"
    entry = ledger[0]
    assert entry["id"] == "R1:row"
    assert entry["type"] == "missing_row"
    assert entry["severity"] == "CRITICAL"
    assert entry["expected"]["row_index"] == 1
    assert entry["detail"]["subsumed_cells"] == 2
    assert entry["detail"]["orphaned_children"] == [2, 14, 43]
    assert report["exit_code"] == 1


# =====================================================================
# 14. Waiver Applies
# =====================================================================
def test_14_waiver_applies(gold_data):
    """Test 14: Apply valid waiver matching id, type, and actual.
    Expect entry marked waived=True, exit_code=0."""
    # PREDICTION:
    # - Mutation: R12:C2 "△0" -> "0"
    # - Waiver provided for R12:C2, sign_error, actual="0", with reason
    # - Entry is marked waived=True, waiver_reason="Verified acceptable"
    # - exit_code: 0
    perturbed = copy.deepcopy(gold_data)
    perturbed["rows"][11]["values"][1] = "0"

    waivers = [
        {
            "id": "R12:C2",
            "type": "sign_error",
            "actual": "0",
            "reason": "Verified acceptable notation difference for negative zero"
        }
    ]

    report = evaluate_table(gold_data, perturbed, waivers=waivers)
    ledger = report["ledger"]
    assert len(ledger) == 1
    assert ledger[0]["waived"] is True
    assert ledger[0]["waiver_reason"] == "Verified acceptable notation difference for negative zero"
    assert report["exit_code"] == 0
    assert report["summary"]["unwaived"] == 0
    assert report["summary"]["waived"] == 1


# =====================================================================
# 15. Waiver Does Not Apply When Actual Changed
# =====================================================================
def test_15_waiver_does_not_apply_when_actual_changed(gold_data):
    """Test 15: Waiver expects actual="0", but actual mutated value is "999".
    Waiver must NOT match, entry remains unwaived, exit_code=1."""
    # PREDICTION:
    # - Mutation: R12:C2 "△0" -> "999" (wrong_printed_value)
    # - Waiver is for R12:C2, sign_error, actual="0"
    # - Neither type nor actual matches -> entry remains unwaived
    # - Waiver listed under stale_waivers
    # - exit_code: 1
    perturbed = copy.deepcopy(gold_data)
    perturbed["rows"][11]["values"][1] = "999"

    waivers = [
        {
            "id": "R12:C2",
            "type": "sign_error",
            "actual": "0",
            "reason": "Verified acceptable notation difference for negative zero"
        }
    ]

    report = evaluate_table(gold_data, perturbed, waivers=waivers)
    ledger = report["ledger"]
    assert len(ledger) == 1
    assert ledger[0]["waived"] is False
    assert report["exit_code"] == 1
    assert len(report["stale_waivers"]) == 1
    assert report["stale_waivers"][0]["id"] == "R12:C2"


# =====================================================================
# 16. Malformed Waiver File Exits 2
# =====================================================================
def test_16_malformed_waiver_exit_2(tmp_path):
    """Test 16: Empty reason in waiver file must trigger exit 2 (harness error)."""
    # PREDICTION:
    # - CLI call with waiver file with empty reason -> exit code 2
    waiver_file = tmp_path / "bad_waiver.json"
    waiver_file.write_text(json.dumps([
        {"id": "R12:C2", "type": "sign_error", "actual": "0", "reason": "   "}
    ]), encoding="utf-8")

    cmd = [
        sys.executable, str(EVALUATE_PY),
        "--gold", str(GOLD_PATH),
        "--input", str(GOLD_PATH),
        "--waivers", str(waiver_file)
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 2, f"Expected returncode 2, got {proc.returncode}. Output:\n{proc.stderr}"
    assert "reason" in proc.stderr.lower()


# =====================================================================
# 17. Malformed Parser Input File Exits 2
# =====================================================================
def test_17_malformed_input_exit_2(tmp_path):
    """Test 17: Schema-invalid parser input (missing 'rows') must trigger exit 2."""
    # PREDICTION:
    # - CLI call with invalid input json missing 'rows' -> exit code 2
    bad_input = tmp_path / "bad_input.json"
    bad_input.write_text(json.dumps({"invalid_root": True}), encoding="utf-8")

    cmd = [
        sys.executable, str(EVALUATE_PY),
        "--gold", str(GOLD_PATH),
        "--input", str(bad_input)
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 2, f"Expected returncode 2, got {proc.returncode}. Output:\n{proc.stderr}"


# =====================================================================
# 18. Stale Waiver Listed as Warning
# =====================================================================
def test_18_stale_waiver_listed(gold_data):
    """Test 18: A waiver for an ID not present in the ledger is listed under stale_waivers."""
    # PREDICTION:
    # - Gold vs Gold -> 0 discrepancies
    # - Waiver provided for R99:C1 -> stale waiver
    # - report["stale_waivers"] has 1 entry
    # - exit_code: 0 (non-gating warning)
    waivers = [
        {
            "id": "R99:C1",
            "type": "wrong_printed_value",
            "actual": "foo",
            "reason": "Historical waiver for obsolete row"
        }
    ]
    report = evaluate_table(gold_data, gold_data, waivers=waivers)
    assert report["ledger"] == []
    assert len(report["stale_waivers"]) == 1
    assert report["stale_waivers"][0]["id"] == "R99:C1"
    assert report["exit_code"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
