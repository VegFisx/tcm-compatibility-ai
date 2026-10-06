# D:\TCMAI\scripts\crawl\clean_zero.py
import sqlite3

DB = r"D:\TCMAI\tcm.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

# 1. 看清理前有多少
cur.execute("SELECT COUNT(*) FROM crawl_progress WHERE n_compounds = 0")
print("清理前 crawl_progress 里 n_compounds=0 的记录数：", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM herb_compound WHERE match_source = 'HERB_detail'")
print("清理前 herb_compound 里 HERB_detail 的记录数：", cur.fetchone()[0])

# 2. 清理
cur.execute("DELETE FROM crawl_progress WHERE n_compounds = 0")
cur.execute("DELETE FROM herb_compound WHERE match_source = 'HERB_detail'")
conn.commit()

# 3. 看清理后
cur.execute("SELECT COUNT(*) FROM crawl_progress WHERE n_compounds = 0")
print("清理后 crawl_progress 里 n_compounds=0 的记录数：", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM herb_compound WHERE match_source = 'HERB_detail'")
print("清理后 herb_compound 里 HERB_detail 的记录数：", cur.fetchone()[0])

conn.close()
print("完成")