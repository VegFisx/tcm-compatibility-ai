# D:\TCMAI\scripts\query\query_coconut.py
import sqlite3
import argparse

DB = r"D:\TCMAI\coconut.db"


def query_species(species, limit=None, with_smiles_only=True):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    sql = """
    SELECT c.cnp_id, c.name, c.formula, c.np_likeness,
           c.chemical_class, c.smiles
    FROM species_compound sc
    JOIN compounds c ON c.cnp_id = sc.cnp_id
    WHERE sc.species = ?
    """
    if with_smiles_only:
        sql += " AND c.smiles IS NOT NULL AND c.smiles != ''"
    sql += " ORDER BY c.cnp_id"
    if limit:
        sql += f" LIMIT {int(limit)}"

    cur.execute(sql, (species.lower().strip(),))
    rows = cur.fetchall()
    conn.close()
    return rows


def query_genus(genus, limit=None, with_smiles_only=True):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    sql = """
    SELECT c.cnp_id, c.name, c.formula, c.np_likeness,
           c.chemical_class, c.smiles
    FROM genus_compound gc
    JOIN compounds c ON c.cnp_id = gc.cnp_id
    WHERE gc.genus = ?
    """
    if with_smiles_only:
        sql += " AND c.smiles IS NOT NULL AND c.smiles != ''"
    sql += " ORDER BY c.cnp_id"
    if limit:
        sql += f" LIMIT {int(limit)}"

    cur.execute(sql, (genus.lower().strip(),))
    rows = cur.fetchall()
    conn.close()
    return rows


def search_species(keyword, limit=20):
    """模糊搜索物种名"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
    SELECT species, COUNT(*) AS n
    FROM species_compound
    WHERE species LIKE ?
    GROUP BY species
    ORDER BY n DESC
    LIMIT ?
    """, (f"%{keyword.lower()}%", limit))
    rows = cur.fetchall()
    conn.close()
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?", help="物种拉丁名 / 属名 / 搜索关键词")
    parser.add_argument("--genus", action="store_true", help="按属名匹配")
    parser.add_argument("--search", action="store_true", help="模糊搜索物种名")
    parser.add_argument("--limit", type=int, default=20, help="返回上限")
    args = parser.parse_args()

    if not args.name:
        print("用法: python query_coconut.py 'Glycyrrhiza uralensis'")
        print("      python query_coconut.py 'Glycyrrhiza' --genus")
        print("      python query_coconut.py 'ginseng' --search")
        return

    if args.search:
        print(f"=== 模糊搜索 '{args.name}' ===")
        rows = search_species(args.name, args.limit)
        for species, n in rows:
            print(f"  {species:40s} {n} 个化合物")
        return

    if args.genus:
        rows = query_genus(args.name, args.limit)
        print(f"=== 属 '{args.name}' 成分（前 {len(rows)} 个）===")
    else:
        rows = query_species(args.name, args.limit)
        print(f"=== 种 '{args.name}' 成分（前 {len(rows)} 个）===")

    if not rows:
        print("未找到")
        return

    for r in rows:
        cnp, name, formula, np_likeness, chem_class, smiles = r
        name_show = name if name else "(无名称)"
        print(f"\n  {cnp}")
        print(f"    名称: {name_show}")
        print(f"    分子式: {formula}")
        print(f"    np_likeness: {np_likeness}")
        print(f"    化学分类: {chem_class}")
        print(f"    SMILES: {smiles[:80]}{'...' if len(smiles) > 80 else ''}")


if __name__ == "__main__":
    main()# 1. 甘草（Glycyrrhiza uralensis）