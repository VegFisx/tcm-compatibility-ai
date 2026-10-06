# D:\TCMAI\scripts\crawl\check_progress.py
import sqlite3

DB = r"D:\TCMAI\tcm.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

print("=== herb_compound 概况 ===")
cur.execute("SELECT COUNT(*) FROM herb_compound")
print("总关系数:", cur.fetchone()[0])

cur.execute("SELECT match_source, COUNT(*) FROM herb_compound GROUP BY match_source")
print("按来源统计:")
for row in cur.fetchall():
    print("   ", row)

cur.execute("SELECT COUNT(DISTINCT herb_id) FROM herb_compound")
print("覆盖药材数:", cur.fetchone()[0])

print()
print("=== crawl_progress 概况 ===")
cur.execute("SELECT status, COUNT(*) FROM crawl_progress GROUP BY status")
for row in cur.fetchall():
    print("   ", row)

print()
print("=== 无效成分检查 ===")
cur.execute("""
SELECT COUNT(*)
FROM herb_compound hc
LEFT JOIN compounds c ON c.ingredient_id = hc.ingredient_id
WHERE c.ingredient_id IS NULL
""")
print("关系里的无效成分数:", cur.fetchone()[0])

print()
print("=== 前 5 条 HERB_detail 关系 ===")
cur.execute("""
SELECT herb_id, ingredient_id, match_level, match_source
FROM herb_compound
WHERE match_source='HERB_detail'
LIMIT 5
""")
for row in cur.fetchall():
    print("   ", row)

conn.close()