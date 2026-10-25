import ast
import glob
from pathlib import Path

py_files = sorted(glob.glob("parser/*.py") + ["main.py"])

print("=== LITERAL NUMBERS & STRINGS AUDIT ===")
for pf in py_files:
    tree = ast.parse(Path(pf).read_text(encoding="utf-8"), filename=pf)
    numbers = []
    strings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                numbers.append((node.lineno, node.value))
            elif isinstance(node.value, str):
                val = node.value.strip()
                # filter out empty, single char formatting, docstrings if multiline
                if len(val) > 1 and "\n" not in val:
                    strings.append((node.lineno, val))
    print(f"\n--- {pf} ---")
    print(f"Numbers ({len(numbers)}):")
    for lineno, val in sorted(numbers):
        print(f"  L{lineno}: {val}")
    print(f"Strings ({len(strings)}):")
    for lineno, val in sorted(strings):
        print(f"  L{lineno}: {repr(val)}")
