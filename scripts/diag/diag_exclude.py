# -*- coding: utf-8 -*-
"""验证 exclude 是否生效"""
import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(r"D:\TCMAI")
DB = str(ROOT / "tcm.db")

# ---- 1. 看 HERB 里所有 "附子" 相关药材 ----
conn = sqlite3.connect(DB)
cur = conn.cursor()

print("=== HERB 里的 '附子' 相关药材 ===")
for r in cur.execute(
    "SELECT herb_id, name_cn FROM herbs WHERE name_cn LIKE '%附子%'"
):
    print("  ", r)

print("\n=== '甘草' 相关药材 ===")
for r in cur.execute(
    "SELECT herb_id, name_cn FROM herbs WHERE name_cn LIKE '%甘草%'"
):
    print("  ", r)

print("\n=== '人参' 相关药材 ===")
for r in cur.execute(
    "SELECT herb_id, name_cn FROM herbs WHERE name_cn LIKE '%人参%'"
):
    print("  ", r)

# ---- 2. 附子的成分数（含/不含白附子）----
print("\n=== 附子：含白附子 vs 不含白附子 成分数 ===")
cur.execute("""
    SELECT COUNT(DISTINCT c.ingredient_id)
    FROM herb_compound hc
    JOIN compounds c ON hc.ingredient_id = c.ingredient_id
    JOIN herbs h ON hc.herb_id = h.herb_id
    WHERE h.name_cn LIKE '%附子%'
      AND c.smiles IS NOT NULL AND c.smiles != ''
""")
n_all = cur.fetchone()[0]
print(f"  含白附子: {n_all}")

cur.execute("""
    SELECT COUNT(DISTINCT c.ingredient_id)
    FROM herb_compound hc
    JOIN compounds c ON hc.ingredient_id = c.ingredient_id
    JOIN herbs h ON hc.herb_id = h.herb_id
    WHERE h.name_cn LIKE '%附子%'
      AND h.name_cn NOT LIKE '%白附子%'
      AND h.name_cn NOT LIKE '%关白附%'
      AND c.smiles IS NOT NULL AND c.smiles != ''
""")
n_ex = cur.fetchone()[0]
print(f"  不含白附子: {n_ex}")

conn.close()

# ---- 3. 看 CSV 里附子部分具体拿了哪些药材 ----
print("\n=== admet_predictions.csv 里附子部分的 herb_name 分布 ===")
df = pd.read_csv(ROOT / "docs" / "admet_predictions.csv")
fz = df[df["herb_query"] == "附子"]
print(f"  总行数: {len(fz)}")
print("  来源分布:")
print(fz["herb_name"].value_counts().to_string())

print("\n=== 甘草部分 ===")
gc = df[df["herb_query"] == "甘草"]
print(f"  总行数: {len(gc)}")
print("  来源分布:")
print(gc["herb_name"].value_counts().to_string())