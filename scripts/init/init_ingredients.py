import pandas as pd
import sqlite3
import math

FILE = r"D:\TCMAI\data\herb\HERB_ingredient_info_v2.txt"

df = pd.read_csv(FILE, sep="\t", encoding="utf-8", low_memory=False)
print("总记录数:", len(df))
print("有 SMILES 的:", df["Canonical_smiles"].notna().sum())

conn = sqlite3.connect(r"D:\TCMAI\tcm.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS compounds (
    ingredient_id   TEXT PRIMARY KEY,
    name_en         TEXT,
    alias           TEXT,
    formula         TEXT,
    smiles          TEXT,
    isomeric_smiles TEXT,
    inchi_key       TEXT,
    mol_weight      REAL,
    drug_likeness   REAL,
    ob_score        REAL,
    cas_id          TEXT,
    pubchem_id      TEXT,
    tcmsp_id        TEXT,
    tcmid_id        TEXT,
    symmap_id       TEXT
)
""")

cur.execute("CREATE INDEX IF NOT EXISTS idx_comp_name ON compounds(name_en)")


def parse_number(v):
    """处理 '39.7;59.9' 这种多值情况，取第一个"""
    if pd.isna(v):
        return None
    s = str(v).strip()
    if not s or s in ("NA", "nan"):
        return None
    # 多个值用分号分隔，取第一个
    if ";" in s:
        s = s.split(";")[0].strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse_str(v):
    """处理 NaN，返回 None 或字符串"""
    if pd.isna(v):
        return None
    s = str(v).strip()
    return s if s and s != "nan" else None


count = 0
for _, row in df.iterrows():
    if pd.isna(row["Canonical_smiles"]):
        continue
    cur.execute("""
        INSERT OR IGNORE INTO compounds VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        str(row["Ingredient_id"]),
        parse_str(row["Ingredient_name"]),
        parse_str(row["Ingredient_alias_name"]),
        parse_str(row["Molecular_formula"]),
        row["Canonical_smiles"],
        parse_str(row["Isomeric_smiles"]),
        parse_str(row["InChIKey"]),
        parse_number(row["MolWt"]),
        parse_number(row["Drug_likeness"]),
        parse_number(row["OB_score"]),
        parse_str(row["CAS_id"]),
        parse_str(row["PubChem_id"]),
        parse_str(row["TCMSP_id"]),
        parse_str(row["TCMID_id"]),
        parse_str(row["SymMap_id"]),
    ))
    count += 1

conn.commit()
cur.execute("SELECT COUNT(*) FROM compounds")
print("导入成功:", cur.fetchone()[0])

cur.execute("SELECT name_en, formula, ob_score, drug_likeness FROM compounds LIMIT 5")
for r in cur.fetchall():
    print(" ", r)

conn.close()