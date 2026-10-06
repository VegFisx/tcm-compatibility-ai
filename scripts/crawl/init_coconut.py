# D:\TCMAI\scripts\crawl\init_coconut.py
import os
import pickle
import sqlite3
from datetime import datetime

COCONUT_DIR = r"D:\TCMAI\archive\deprecated\coconut"
SPECIES_PKL = os.path.join(COCONUT_DIR, "species_index.pkl")
DB = r"D:\TCMAI\coconut.db"


def main():
    if not os.path.exists(SPECIES_PKL):
        print("找不到 species_index.pkl")
        return

    print("加载 species_index.pkl ...")
    with open(SPECIES_PKL, "rb") as f:
        data = pickle.load(f)

    species_index = data.get("species_index", {})
    genus_index = data.get("genus_index", {})

    print(f"  species 数量: {len(species_index)}")
    print(f"  genus 数量: {len(genus_index)}")

    # 建库
    print(f"\n建库: {DB}")
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.executescript("""
    DROP TABLE IF EXISTS compounds;
    DROP TABLE IF EXISTS species_compound;
    DROP TABLE IF EXISTS genus_compound;

    CREATE TABLE compounds (
        cnp_id TEXT PRIMARY KEY,
        name TEXT,
        smiles TEXT,
        formula TEXT,
        np_likeness REAL,
        chemical_class TEXT,
        chemical_sub_class TEXT,
        chemical_super_class TEXT
    );

    CREATE TABLE species_compound (
        species TEXT,
        cnp_id TEXT,
        PRIMARY KEY (species, cnp_id)
    );

    CREATE TABLE genus_compound (
        genus TEXT,
        cnp_id TEXT,
        PRIMARY KEY (genus, cnp_id)
    );
    """)
    conn.commit()

    # 收集所有化合物 + 关系
    print("\n写入 compounds ...")
    compounds = {}
    species_rows = []
    genus_rows = []

    for species, items in species_index.items():
        s_lower = species.lower().strip()
        for item in items:
            if not isinstance(item, dict):
                continue
            cnp = item.get("identifier")
            if not cnp:
                continue
            if cnp not in compounds:
                compounds[cnp] = (
                    cnp,
                    item.get("name") if not _is_nan(item.get("name")) else None,
                    item.get("smiles"),
                    item.get("formula"),
                    item.get("np_likeness"),
                    item.get("chemical_class"),
                    item.get("chemical_sub_class"),
                    item.get("chemical_super_class"),
                )
            species_rows.append((s_lower, cnp))

    for genus, items in genus_index.items():
        g_lower = genus.lower().strip()
        for item in items:
            if not isinstance(item, dict):
                continue
            cnp = item.get("identifier")
            if not cnp:
                continue
            if cnp not in compounds:
                compounds[cnp] = (
                    cnp,
                    item.get("name") if not _is_nan(item.get("name")) else None,
                    item.get("smiles"),
                    item.get("formula"),
                    item.get("np_likeness"),
                    item.get("chemical_class"),
                    item.get("chemical_sub_class"),
                    item.get("chemical_super_class"),
                )
            genus_rows.append((g_lower, cnp))

    print(f"  去重后化合物数: {len(compounds)}")
    print(f"  species_compound 关系: {len(species_rows)}")
    print(f"  genus_compound 关系: {len(genus_rows)}")

    print("\n批量写入 ...")
    cur.executemany(
        "INSERT OR IGNORE INTO compounds VALUES (?,?,?,?,?,?,?,?)",
        list(compounds.values())
    )
    cur.executemany(
        "INSERT OR IGNORE INTO species_compound VALUES (?,?)",
        species_rows
    )
    cur.executemany(
        "INSERT OR IGNORE INTO genus_compound VALUES (?,?)",
        genus_rows
    )
    conn.commit()

    # 建索引
    print("建索引 ...")
    cur.executescript("""
    CREATE INDEX idx_species ON species_compound(species);
    CREATE INDEX idx_genus ON genus_compound(genus);
    CREATE INDEX idx_cnp ON species_compound(cnp_id);
    """)
    conn.commit()

    # 统计
    cur.execute("SELECT COUNT(*) FROM compounds")
    print(f"\ncompounds 总数: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM species_compound")
    print(f"species_compound 总数: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM genus_compound")
    print(f"genus_compound 总数: {cur.fetchone()[0]}")

    # 抽 5 个物种看看
    cur.execute("""
    SELECT species, COUNT(*) AS n
    FROM species_compound
    GROUP BY species
    ORDER BY n DESC
    LIMIT 10
    """)
    print("\n成分最多的 10 个物种:")
    for row in cur.fetchall():
        print(f"  {row[0]} -> {row[1]} 个化合物")

    conn.close()
    print("\n完成")


def _is_nan(x):
    try:
        return x != x
    except Exception:
        return False


if __name__ == "__main__":
    t0 = datetime.now()
    main()
    print(f"\n耗时: {datetime.now() - t0}")