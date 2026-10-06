# -*- coding: utf-8 -*-
"""统计 COCONUT 数据库规模"""
import sqlite3
from pathlib import Path

DB = r"D:\TCMAI\coconut.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

print("=== COCONUT 数据库统计 ===\n")

# 表行数
for tbl in ['compounds', 'species_compound', 'genus_compound']:
    cur.execute(f"SELECT COUNT(*) FROM {tbl}")
    n = cur.fetchone()[0]
    print(f"  {tbl:20s}: {n:>10,} 行")

# 物种/属数量
cur.execute("SELECT COUNT(DISTINCT species) FROM species_compound")
n_species = cur.fetchone()[0]
cur.execute("SELECT COUNT(DISTINCT genus) FROM genus_compound")
n_genus = cur.fetchone()[0]
print(f"\n  不同物种数: {n_species:,}")
print(f"  不同属数:   {n_genus:,}")

# 带 SMILES 的化合物数
cur.execute("""
    SELECT COUNT(*) FROM compounds
    WHERE smiles IS NOT NULL
      AND smiles != ''
      AND smiles != 'None'
      AND LENGTH(smiles) > 5
""")
n_valid = cur.fetchone()[0]
print(f"\n  有效 SMILES 的化合物: {n_valid:,}")

# 各物种 Top 10（成分最多的）
print("\n=== 成分最多的 10 个物种 ===")
cur.execute("""
    SELECT species, COUNT(*) AS n
    FROM species_compound
    GROUP BY species
    ORDER BY n DESC
    LIMIT 10
""")
for sp, n in cur.fetchall():
    print(f"  {sp:40s}  {n:>6,}")

# 你关心的几个物种
print("\n=== 你项目里用到的物种 ===")
targets = [
    "aconitum carmichaelii",
    "glycyrrhiza uralensis",
    "panax ginseng",
    "euphorbia pekinensis",
    "veratrum nigrum",
    "pinellia ternata",
    "rheum palmatum",
]
for sp in targets:
    cur.execute("""
        SELECT COUNT(*) FROM species_compound
        WHERE LOWER(species) LIKE ?
    """, (f"%{sp}%",))
    n = cur.fetchone()[0]
    print(f"  {sp:40s}  {n:>6,}")

conn.close()