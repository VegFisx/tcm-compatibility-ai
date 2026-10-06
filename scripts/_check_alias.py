# -*- coding: utf-8 -*-
import sqlite3
c = sqlite3.connect(r"D:\TCMAI\tcm.db")
cur = c.cursor()

# 总数
n = cur.execute("SELECT COUNT(*) FROM herbs").fetchone()[0]
print(f"herbs 表共 {n} 条\n")

# 有 alias 的有几条
n_alias = cur.execute("SELECT COUNT(*) FROM herbs WHERE alias IS NOT NULL AND alias != ''").fetchone()[0]
print(f"其中 alias 非空: {n_alias}\n")

# 看几个样例（挑几个常见药）
print("=== 样例 ===")
for name in ["甘草", "附子", "元参", "玄参", "山药", "大黄", "生地", "熟地", "陈皮"]:
    row = cur.execute(
        "SELECT name_cn, alias FROM herbs WHERE name_cn = ?", (name,)
    ).fetchone()
    if row:
        print(f"{row[0]!r:8s} alias={row[1]!r}")
    else:
        print(f"{name!r:8s} 库里没有")

print("\n=== 前 5 条含 alias 的记录 ===")
for r in cur.execute("SELECT name_cn, alias FROM herbs WHERE alias IS NOT NULL AND alias != '' LIMIT 5"):
    print(f"  {r[0]!r}  →  {r[1]!r}")

c.close()