# -*- coding: utf-8 -*-
import sqlite3

c = sqlite3.connect(r"D:\TCMAI\tcm.db")
print("=== tcm.db 所有表 ===")
for name, sql in c.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"):
    print(f"\n--- {name} ---")
    print(sql)
c.close()