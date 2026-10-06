# -*- coding: utf-8 -*-
"""核实图2的三个化合物：Aconitine / Benzoylaconine / Aconine"""
import sys
import sqlite3
sys.path.insert(0, r"D:\TCMAI\src")
from admet_cache import ADMETCache
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

# 三个化合物的中文/英文名，用于在 tcm.db 里查
NAMES = ["Aconitine", "Benzoylaconine", "Aconine",
         "乌头碱", "苯甲酰乌头原碱", "乌头原碱",
         "aconitine", "benzoylaconine", "aconine"]

c = sqlite3.connect(r"D:\TCMAI\tcm.db")
cur = c.cursor()

print("=== 在 tcm.db 里查这三个化合物 ===\n")
found = {}
for n in NAMES:
    rows = cur.execute(
        "SELECT ingredient_id, name_en, alias, smiles FROM compounds "
        "WHERE name_en LIKE ? OR alias LIKE ? LIMIT 3",
        (f"%{n}%", f"%{n}%")
    ).fetchall()
    for r in rows:
        ing_id, name_en, alias, smiles = r
        if smiles and ing_id not in found:
            found[ing_id] = (name_en, smiles)
c.close()

if not found:
    print("[未找到] tcm.db 里没有这三个化合物，可能名字写法不同")
else:
    print(f"找到 {len(found)} 个\n")

    cache = ADMETCache()
    print(f"ADMET 缓存: {cache.size()} 条\n")
    print(f"{'名称':30s} {'分子量':>10s} {'分子式':>15s} {'hERG':>10s}")
    print("-" * 70)

    for ing_id, (name, smiles) in found.items():
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            print(f"{name:30s}  [SMILES 解析失败]")
            continue
        mw = round(Descriptors.MolWt(mol), 2)
        formula = rdMolDescriptors.CalcMolFormula(mol)
        rec = cache.get(smiles)
        herg = rec.get("hERG") if rec else None
        herg_str = f"{herg:.3f}" if herg is not None else "未缓存"
        print(f"{name:30s} {mw:>10.2f} {formula:>15s} {herg_str:>10s}")
    cache.close()