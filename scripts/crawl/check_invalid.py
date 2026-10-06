# D:\TCMAI\scripts\crawl\check_invalid.py
import sqlite3

conn = sqlite3.connect(r"D:\TCMAI\tcm.db")
cur = conn.cursor()

# 1. 唯一的无效 HBIN 有多少
cur.execute("""
SELECT COUNT(DISTINCT hc.ingredient_id)
FROM herb_compound hc
LEFT JOIN compounds c ON c.ingredient_id = hc.ingredient_id
WHERE c.ingredient_id IS NULL
""")
print("唯一无效 HBIN 数:", cur.fetchone()[0])

# 2. 无效 HBIN 影响多少药材
cur.execute("""
SELECT COUNT(DISTINCT hc.herb_id)
FROM herb_compound hc
LEFT JOIN compounds c ON c.ingredient_id = hc.ingredient_id
WHERE c.ingredient_id IS NULL
""")
print("受影响药材数:", cur.fetchone()[0])

# 3. 前 10 个无效 HBIN 及其对应药材
cur.execute("""
SELECT DISTINCT hc.ingredient_id
FROM herb_compound hc
LEFT JOIN compounds c ON c.ingredient_id = hc.ingredient_id
WHERE c.ingredient_id IS NULL
LIMIT 10
""")
invalids = [r[0] for r in cur.fetchall()]
print("\n前 10 个无效 HBIN:", invalids)

# 4. 抽一个看看 HERB 上有没有
if invalids:
    sample = invalids[0]
    cur.execute("""
    SELECT h.name_cn FROM herb_compound hc
    JOIN herbs h ON h.herb_id = hc.herb_id
    WHERE hc.ingredient_id = ?
    LIMIT 5
    """, (sample,))
    print(f"\n{sample} 关联的药材:", [r[0] for r in cur.fetchall()])

conn.close()