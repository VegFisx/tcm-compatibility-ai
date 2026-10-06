# D:\TCMAI\scripts\crawl\analyze_invalid.py
import sqlite3

conn = sqlite3.connect(r"D:\TCMAI\tcm.db")
cur = conn.cursor()

# 每个无效 HBIN 出现在多少味药材中
cur.execute("""
SELECT hc.ingredient_id, COUNT(DISTINCT hc.herb_id) AS n_herbs
FROM herb_compound hc
LEFT JOIN compounds c ON c.ingredient_id = hc.ingredient_id
WHERE c.ingredient_id IS NULL
GROUP BY hc.ingredient_id
ORDER BY n_herbs DESC
""")
rows = cur.fetchall()

print(f"唯一无效 HBIN 总数: {len(rows)}")

# 频率分布
buckets = {"1": 0, "2-4": 0, "5-9": 0, "10-49": 0, "50+": 0}
for _, n in rows:
    if n == 1:
        buckets["1"] += 1
    elif n <= 4:
        buckets["2-4"] += 1
    elif n <= 9:
        buckets["5-9"] += 1
    elif n <= 49:
        buckets["10-49"] += 1
    else:
        buckets["50+"] += 1

print("\n=== 出现频率分布 ===")
for k, v in buckets.items():
    print(f"  出现在 {k:6s} 味药材中: {v:5d} 个 HBIN")

# 累计覆盖药材数
print("\n=== 补不同阈值能覆盖多少关系 ===")
for threshold in [1, 2, 5, 10, 50]:
    hbins = [h for h, n in rows if n >= threshold]
    total_rel = sum(n for _, n in rows if n >= threshold)
    print(f"  >= {threshold:2d} 味: 补 {len(hbins):5d} 个 HBIN → 覆盖 {total_rel:6d} 条关系")

# Top 20 高频无效 HBIN
print("\n=== Top 20 高频无效 HBIN ===")
for h, n in rows[:20]:
    print(f"  {h}  出现在 {n} 味药材")

conn.close()