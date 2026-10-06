# -*- coding: utf-8 -*-
from pathlib import Path
p = Path(r"D:\TCMAI\scripts\plot_detox_pathway.py")
if p.exists():
    lines = p.read_text(encoding="utf-8").splitlines()
    print(f"文件共 {len(lines)} 行\n")
    for i, l in enumerate(lines, 1):
        if any(k in l for k in ["0.614", "0.533", "0.200",
                                "645", "603", "499",
                                "Aconitine", "Benzoyl", "Aconine",
                                "SMILES", "smiles", "herg", "HERG"]):
            print(f"{i:4d}: {l}")
else:
    print("文件不存在")