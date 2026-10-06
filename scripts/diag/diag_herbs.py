# -*- coding: utf-8 -*-
"""诊断药材名 + 成分数"""
import sqlite3
from pathlib import Path

DB = r"D:\TCMAI\tcm.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

# ---- 1. 所有含"戟"的药材 ----
print("=== 含 '戟' 的药材 ===")
for r in cur.execute(
    "SELECT herb_id, name_cn FROM herbs WHERE name_cn LIKE ?", ("%戟%",)
):
    print("  ", r)

# ---- 2. 含"乌头"或"附子"的药材 + 各自成分数 ----
print("\n=== 含 '乌头' 或 '附子' 的药材 + 成分数 ===")
cur.execute("""
    SELECT h.name_cn, COUNT(DISTINCT hc.ingredient_id) AS n
    FROM herbs h
    LEFT JOIN herb_compound hc ON h.herb_id = hc.herb_id
    WHERE h.name_cn LIKE '%乌头%' OR h.name_cn LIKE '%附子%'
    GROUP BY h.name_cn
    ORDER BY n DESC
""")
for r in cur.fetchall():
    print(f"  {r[0]:20s}  {r[1]} 个成分")

# ---- 3. 含"甘草"的药材 + 成分数 ----
print("\n=== 含 '甘草' 的药材 + 成分数 ===")
cur.execute("""
    SELECT h.name_cn, COUNT(DISTINCT hc.ingredient_id) AS n
    FROM herbs h
    LEFT JOIN herb_compound hc ON h.herb_id = hc.herb_id
    WHERE h.name_cn LIKE '%甘草%'
    GROUP BY h.name_cn
    ORDER BY n DESC
""")
for r in cur.fetchall():
    print(f"  {r[0]:20s}  {r[1]} 个成分")

# ---- 4. 含"半夏"的药材 ----
print("\n=== 含 '半夏' 的药材 + 成分数 ===")
cur.execute("""
    SELECT h.name_cn, COUNT(DISTINCT hc.ingredient_id) AS n
    FROM herbs h
    LEFT JOIN herb_compound hc ON h.herb_id = hc.herb_id
    WHERE h.name_cn LIKE '%半夏%'
    GROUP BY h.name_cn
    ORDER BY n DESC
""")
for r in cur.fetchall():
    print(f"  {r[0]:20s}  {r[1]} 个成分")

conn.close()