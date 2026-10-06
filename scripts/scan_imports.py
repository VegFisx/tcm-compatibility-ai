# -*- coding: utf-8 -*-
"""扫描项目里实际被 import 的包，和 requirements.txt 对比"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(r"D:\TCMAI")
SKIP_DIRS = {"venv", "dist", "build", "archive", "backups", ".git", "__pycache__"}
STDLIB = set(sys.stdlib_module_names)

NAME_MAP = {
    "sklearn": "scikit-learn", "PIL": "pillow", "cv2": "opencv-python",
    "dotenv": "python-dotenv", "yaml": "PyYAML", "bs4": "beautifulsoup4",
    "attr": "attrs", "rdkit": "rdkit",
}

imports = set()
for p in ROOT.rglob("*.py"):
    if any(part in SKIP_DIRS for part in p.parts):
        continue
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except Exception:
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imports.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imports.add(node.module.split(".")[0])

normalized = {NAME_MAP.get(m, m).lower() for m in imports if m not in STDLIB}

reqs = set()
for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#"):
        reqs.add(re.split(r"[=<>!]", line)[0].strip().lower())

print("=== 代码里实际 import 的（归一化）===")
for m in sorted(normalized):
    print(f"  {m}")

print("\n=== requirements 里但没被直接 import（候选可删）===")
for r in sorted(reqs - normalized):
    print(f"  {r}")

print("\n=== 被 import 但 requirements 里没有（需补）===")
for n in sorted(normalized - reqs):
    print(f"  {n}")