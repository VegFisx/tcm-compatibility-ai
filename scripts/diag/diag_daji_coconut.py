# -*- coding: utf-8 -*-
"""诊断：COCONUT 里京大戟有多少成分、有没有 SMILES"""
import sqlite3
from pathlib import Path

DB = r"D:\TCMAI\coconut.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

# ---- 1. 看所有表 ----
print("=== COCONUT 所有表 ===")
for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    print("  ", t[0])

# ---- 2. 看关键表的列名 ----
print("\n=== 列名 ===")
for tbl in ['compounds', 'species_compound', 'genus_compound']:
    try:
        cols = [r[1] for r in cur.execute(f'PRAGMA table_info({tbl})')]
        print(f"  {tbl}: {cols}")
    except Exception as e:
        print(f"  {tbl}: ERR {e}")

# ---- 3. 找 "Euphorbia pekinensis" 物种 ----
print("\n=== species_compound 里含 'Euphorbia pekinensis' 的记录 ===")
try:
    # 先看 species 列名
    cols = [r[1] for r in cur.execute('PRAGMA table_info(species_compound)')]
    print(f"  species_compound 列: {cols}")

    # 尝试找 species 名字列
    species_col = None
    for c in cols:
        if 'species' in c.lower() or 'name' in c.lower() or 'organism' in c.lower():
            species_col = c
            break
    if not species_col:
        species_col = cols[1] if len(cols) > 1 else cols[0]

    print(f"  用列 '{species_col}' 查找")
    cur.execute(f"""
        SELECT * FROM species_compound
        WHERE {species_col} LIKE '%Euphorbia pekinensis%'
        LIMIT 5
    """)
    rows = cur.fetchall()
    print(f"  命中 {len(rows)} 条样例:")
    for r in rows:
        print("   ", [str(x)[:60] for x in r])

    # 总数
    cur.execute(f"""
        SELECT COUNT(*) FROM species_compound
        WHERE {species_col} LIKE '%Euphorbia pekinensis%'
    """)
    n = cur.fetchone()[0]
    print(f"\n  Euphorbia pekinensis 相关记录总数: {n}")

    # 看看类似的其它大戟
    print("\n=== 所有 Euphorbia 属物种名 ===")
    cur.execute(f"""
        SELECT DISTINCT {species_col} FROM species_compound
        WHERE {species_col} LIKE '%Euphorbia%'
        LIMIT 30
    """)
    for r in cur.fetchall():
        print("  ", r[0])

except Exception as e:
    print(f"  ERR: {e}")

# ---- 4. 看 compounds 表里有没有 SMILES ----
print("\n=== compounds 表结构 ===")
try:
    cols = [r[1] for r in cur.execute('PRAGMA table_info(compounds)')]
    print(f"  columns: {cols}")
    cur.execute("SELECT * FROM compounds LIMIT 3")
    for r in cur.fetchall():
        print("  sample:", [str(x)[:60] for x in r])
except Exception as e:
    print(f"  ERR: {e}")

conn.close()