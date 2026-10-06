import csv
import sqlite3

conn = sqlite3.connect("tcm.db")
cur = conn.cursor()

# 药材主表（只保留你真正需要的字段，别全塞进去）
cur.execute("""
CREATE TABLE IF NOT EXISTS herbs (
    herb_id       TEXT PRIMARY KEY,
    pinyin        TEXT,
    name_cn       TEXT NOT NULL,
    alias         TEXT,
    name_en       TEXT,
    latin         TEXT,
    properties    TEXT,
    meridians     TEXT,
    use_part      TEXT,
    function      TEXT,
    indication    TEXT,
    toxicity      TEXT,
    tcmsp_id      TEXT,
    tcmid_id      TEXT,
    symmap_id     TEXT,
    tcm_id        TEXT
)
""")

# 建索引，后面按中文名查会非常快
cur.execute("CREATE INDEX IF NOT EXISTS idx_herb_name ON herbs(name_cn)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_herb_tcmsp ON herbs(tcmsp_id)")

def clean(v):
    """把 NA / 空字符串统一成 None"""
    if v is None:
        return None
    v = v.strip()
    if v == "" or v == "NA":
        return None
    return v

with open("HERB_herb_info_v2.txt", encoding="utf-8") as f:
    reader = csv.reader(f, delimiter="\t")
    header = next(reader)  # 跳过表头

    count = 0
    for row in reader:
        if len(row) < 18:
            continue
        cur.execute("""
            INSERT OR IGNORE INTO herbs VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            clean(row[0]),   # Herb_id
            clean(row[1]),   # 拼音
            clean(row[2]),   # 中文名
            clean(row[3]),   # 别名
            clean(row[4]),   # 英文名
            clean(row[5]),   # 拉丁名
            clean(row[6]),   # 性味
            clean(row[7]),   # 归经
            clean(row[8]),   # 药用部位
            clean(row[9]),   # 功效
            clean(row[10]),  # 主治
            clean(row[11]),  # 毒性
            clean(row[16]),  # TCMSP_id
            clean(row[17]),  # TCMID_id
            clean(row[15]),  # SymMap_id
            clean(row[18]) if len(row) > 18 else None,  # TCM_ID_id
        ))
        count += 1

conn.commit()
print(f"成功导入 {count} 条药材记录")

# 自检
cur.execute("SELECT COUNT(*) FROM herbs WHERE name_cn IS NOT NULL")
print("有中文名的药材:", cur.fetchone()[0])
cur.execute("SELECT herb_id, name_cn, properties, toxicity FROM herbs WHERE name_cn IN ('附子','甘草','人参')")
for r in cur.fetchall():
    print(r)

conn.close()