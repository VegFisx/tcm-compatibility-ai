# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path

for db in [r"D:\TCMAI\tcm.db", r"D:\TCMAI\coconut.db"]:
    print(f"\n=== {Path(db).name} ===")
    c = sqlite3.connect(db)
    for name, sql in c.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"):
        print(f"\n--- {name} ---")
        print(sql)
    c.close()