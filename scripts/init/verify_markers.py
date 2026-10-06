import sqlite3

conn = sqlite3.connect(r"D:\TCMAI\tcm.db")
cur = conn.cursor()

for herb_cn in ["附子", "甘草", "人参", "黄连"]:
    print(f"\n{'=' * 60}")
    print(f"【{herb_cn}】")
    print("=" * 60)
    cur.execute("""
        SELECT c.name_en, c.formula
        FROM herb_compound hc
        JOIN herbs h ON hc.herb_id = h.herb_id
        JOIN compounds c ON hc.ingredient_id = c.ingredient_id
        WHERE h.name_cn = ?
        ORDER BY c.name_en
    """, (herb_cn,))
    rows = cur.fetchall()
    print(f"共 {len(rows)} 个成分")
    for name, formula in rows[:15]:
        print(f"  {name}  ({formula})")
    if len(rows) > 15:
        print(f"  ... 还有 {len(rows) - 15} 个")

conn.close()