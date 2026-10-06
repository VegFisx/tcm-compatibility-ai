import sqlite3

conn = sqlite3.connect("tcm.db")
cur = conn.cursor()

# 建表
cur.execute("""CREATE TABLE IF NOT EXISTS herbs (
    herb_id INTEGER PRIMARY KEY,
    herb_name TEXT, pinyin TEXT, category TEXT)""")

cur.execute("""CREATE TABLE IF NOT EXISTS compounds (
    compound_id INTEGER PRIMARY KEY,
    compound_name TEXT, smiles TEXT, pubchem_cid TEXT)""")

cur.execute("""CREATE TABLE IF NOT EXISTS herb_compound (
    herb_id INTEGER, compound_id INTEGER)""")

cur.execute("""CREATE TABLE IF NOT EXISTS toxicity (
    compound_id INTEGER, endpoint TEXT, value TEXT)""")

cur.execute("""CREATE TABLE IF NOT EXISTS herb_compound (
    herb_id INTEGER,
    compound_id INTEGER,
    UNIQUE(herb_id, compound_id))""")

# 插入数据（示例）
herbs = [
    (1, "附子", "Fuzi", "温里药"),
    (2, "甘草", "Gancao", "补虚药"),
    (3, "人参", "Renshen", "补虚药"),
    (4, "黄连", "Huanglian", "清热药"),
    (5, "大黄", "Dahuang", "泻下药"),
]
cur.executemany("INSERT OR IGNORE INTO herbs VALUES (?,?,?,?)", herbs)

compounds = [
    (1, "乌头碱", "CC(=O)OC1CCC2(C)C(=CCC3C2CC...", "CID_1"),
    (2, "甘草酸", "CC(C)C1=CC(=O)C2=C(C1=O)...", "CID_2"),
    # 你继续补到20个
]
cur.executemany("INSERT OR IGNORE INTO compounds VALUES (?,?,?,?)", compounds)

# 关联
cur.executemany("INSERT OR IGNORE INTO herb_compound VALUES (?,?)", [
    (1, 1), (2, 2), (3, 2), (4, 2),  # 示例
])

conn.commit()
conn.close()
print("数据库建好了，文件：tcm.db")