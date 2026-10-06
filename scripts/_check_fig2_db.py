# -*- coding: utf-8 -*-
import sys
import sqlite3
sys.path.insert(0, r"D:\TCMAI\src")
from admet_cache import ADMETCache

c = sqlite3.connect(r"D:\TCMAI\tcm.db")
cur = c.cursor()

# 用关键词查（不区分大小写）
targets = ["aconitine", "benzoylaconine", "aconine"]

print("=== tcm.db 里找到的 ===\n")
found = []
for t in targets:
    rows = cur.execute(
        "SELECT ingredient_id, name_en, smiles FROM compounds "
        "WHERE LOWER(name_en) = ? OR LOWER(name_en) LIKE ? LIMIT 5",
        (t, f"%{t}%")
    ).fetchall()
    for r in rows:
        ing_id, name, smiles = r
        if smiles and not any(f[0] == ing_id for f in found):
            found.append((ing_id, name, smiles))
            print(f"  {name}  (id={ing_id})")
            print(f"    SMILES: {smiles[:80]}")
c.close()

print(f"\n=== 查 ADMET 缓存 ===\n")
cache = ADMETCache()
print(f"{'名称':30s} {'hERG':>10s}")
print("-" * 45)
for ing_id, name, smiles in found:
    rec = cache.get(smiles)
    if rec:
        print(f"{name:30s} {rec.get('hERG', 'N/A'):>10}")
    else:
        print(f"{name:30s} {'未缓存':>10}")
cache.close()