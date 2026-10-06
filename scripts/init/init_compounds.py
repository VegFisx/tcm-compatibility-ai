import csv
import sqlite3

conn = sqlite3.connect(r"D:\TCMAI\tcm.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS compounds (
    compound_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name_en       TEXT,
    formula       TEXT,
    dl_weight     REAL,
    dl_grade      TEXT,
    smiles        TEXT,
    pubchem_cid   TEXT,
    UNIQUE(name_en, formula)
)
""")

def clean(v):
    if v is None:
        return None
    v = v.strip().strip('"')
    return None if v in ("", "NA") else v

with open(r"D:\TCMAI\tableExport.txt", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    print("表头:", header)
    count = 0
    for row in reader:
        if len(row) < 4:
            continue
        name = clean(row[0])
        formula = clean(row[1])
        dl_w = clean(row[2])
        grade = clean(row[3])
        if not name:
            continue
        cur.execute("""
            INSERT OR IGNORE INTO compounds (name_en, formula, dl_weight, dl_grade)
            VALUES (?,?,?,?)
        """, (name, formula, float(dl_w) if dl_w else None, grade))
        count += 1

conn.commit()

cur.execute("SELECT COUNT(*) FROM compounds")
print("compounds 表总记录数:", cur.fetchone()[0])

cur.execute("SELECT name_en, formula, dl_grade FROM compounds LIMIT 5")
for r in cur.fetchall():
    print(" ", r)

conn.close()