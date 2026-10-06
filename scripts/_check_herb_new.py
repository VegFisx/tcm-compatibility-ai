# -*- coding: utf-8 -*-
from pathlib import Path

for f in ["HERB_experiment_info_v2.txt", "HERB_formula_info_v2.txt"]:
    p = Path.home() / "Downloads" / f
    print(f"\n{'='*60}\n=== {f} ===\n{'='*60}")
    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    print(f"总行数: {len(lines)}")
    print("\n[表头]")
    print(lines[0])
    print("\n[前 3 行数据]")
    for l in lines[1:4]:
        print(l[:400])