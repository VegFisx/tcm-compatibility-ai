# D:\TCMAI\scripts\crawl\crawl_ingredients.py
"""
用 HERB 的 Ingredient API 补 compounds 表
只补 >= MIN_HERB_COUNT 味药材中出现的无效 HBIN
"""
import os
import re
import time
import random
import sqlite3
import argparse
from datetime import datetime

import requests

DB = r"D:\TCMAI\tcm.db"
API = "http://herb.ac.cn/chedi/api/"
MIN_HERB_COUNT = 5   # 补 >= 5 味药材中出现的

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "http://herb.ac.cn",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/152.0.0.0 Safari/537.36 Edg/152.0.0.0",
}


def now():
    return datetime.now().isoformat(timespec="seconds")


def get_conn():
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_tables(conn):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS ingredient_progress (
        hbin TEXT PRIMARY KEY,
        status TEXT DEFAULT 'pending',
        http_status INTEGER,
        error TEXT,
        updated_at TEXT
    )
    """)
    # 检查 compounds 表的列
    cols = [r[1] for r in conn.execute("PRAGMA table_info(compounds)").fetchall()]
    print("compounds 现有列:", cols)
    conn.commit()


def get_invalid_hbins(conn, min_herb_count):
    """找无效的 HBIN，按出现频率从高到低排序"""
    sql = """
    SELECT hc.ingredient_id, COUNT(DISTINCT hc.herb_id) AS n
    FROM herb_compound hc
    LEFT JOIN compounds c ON c.ingredient_id = hc.ingredient_id
    WHERE c.ingredient_id IS NULL
      AND hc.ingredient_id NOT IN (SELECT hbin FROM ingredient_progress WHERE status='done')
    GROUP BY hc.ingredient_id
    HAVING n >= ?
    ORDER BY n DESC
    """
    return conn.execute(sql, (min_herb_count,)).fetchall()


def fetch_ingredient(hbin):
    payload = {
        "v": hbin,
        "label": "Ingredient",
        "key_id": hbin,
        "func_name": "detail_api",
    }
    headers = dict(HEADERS)
    headers["Referer"] = f"http://herb.ac.cn/Detail/?v={hbin}&label=Ingredient"
    r = requests.post(API, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    return r.json(), r.status_code


def _clean(v):
    """把 dict/list 等复杂类型转成字符串，其他原样返回"""
    if v is None:
        return None
    if isinstance(v, dict):
        # 常见形式 {'link': ..., 'title': ...}
        if "title" in v:
            return str(v["title"])
        if "link" in v:
            return str(v["link"])
        return str(v)
    if isinstance(v, (list, tuple)):
        # 列表形式，拼接或取首元素
        parts = [_clean(x) for x in v]
        parts = [p for p in parts if p]
        return "; ".join(parts) if parts else None
    if isinstance(v, float) and v != v:  # NaN
        return None
    return v


def parse_summary(data):
    """从 summary 字段里提取信息"""
    summary = data.get("summary") or []
    if len(summary) < 2:
        return None
    header = summary[0]
    values = summary[1]
    row = dict(zip(header, values))

    return {
        "ingredient_id": _clean(row.get("Ingredient id")),
        "name_en": _clean(row.get("Ingredient name")),
        "alias": _clean(row.get("Alias")),
        "formula": _clean(row.get("Molecule formula")),
        "smiles": _clean(row.get("Molecule smile")),
        "mol_weight": _clean(row.get("Molecule weight")),
        "ob_score": _clean(row.get("OB score")),
        "cas_id": _clean(row.get("CAS id")),
        "symmap_id": _clean(row.get("SymMap id")),
        "tcmsp_id": _clean(row.get("TCMSP id")),
        "pubchem_id": _clean(row.get("PubChem id")),
    }


def insert_compound(conn, info):
    """向 compounds 表插入。只插现有列中有的字段"""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(compounds)").fetchall()]
    row = {k: info.get(k) for k in cols if k in info}
    if "ingredient_id" not in row or not row["ingredient_id"]:
        return False
    placeholders = ",".join(["?"] * len(row))
    colnames = ",".join(row.keys())
    try:
        conn.execute(
            f"INSERT OR IGNORE INTO compounds ({colnames}) VALUES ({placeholders})",
            list(row.values())
        )
        return True
    except Exception as e:
        print(f"    插入失败: {e}")
        return False


def save_done(conn, hbin, status, http_status=None, error=None):
    conn.execute("""
    INSERT OR REPLACE INTO ingredient_progress
    (hbin, status, http_status, error, updated_at)
    VALUES (?, ?, ?, ?, ?)
    """, (hbin, status, http_status, error, now()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="只爬前 N 个，测试用")
    parser.add_argument("--min-herbs", type=int, default=MIN_HERB_COUNT)
    args = parser.parse_args()

    conn = get_conn()
    init_tables(conn)

    tasks = get_invalid_hbins(conn, args.min_herbs)
    print(f"待爬 HBIN 数（出现在 >= {args.min_herbs} 味药材中）：{len(tasks)}")
    if args.limit:
        tasks = tasks[:args.limit]
        print(f"限制为前 {args.limit} 个")

    total_ok = 0
    total_fail = 0
    total_no_smiles = 0
    total_inserted = 0

    for i, (hbin, n_herbs) in enumerate(tasks, 1):
        try:
            data, status = fetch_ingredient(hbin)
            info = parse_summary(data)

            if not info or not info.get("smiles"):
                total_no_smiles += 1
                save_done(conn, hbin, "no_smiles", status)
                print(f"[{i}/{len(tasks)}] {hbin} ({n_herbs}味) → 无 SMILES")
                conn.commit()
                time.sleep(random.uniform(1.2, 2.0))
                continue

            if insert_compound(conn, info):
                total_inserted += 1

            save_done(conn, hbin, "done", status)
            total_ok += 1
            print(f"[{i}/{len(tasks)}] {hbin} ({n_herbs}味) → {info['name_en']}")
            conn.commit()

        except Exception as e:
            total_fail += 1
            save_done(conn, hbin, "failed", error=str(e)[:300])
            conn.commit()
            print(f"[{i}/{len(tasks)}] {hbin} 失败: {e}")

        time.sleep(random.uniform(1.2, 2.0))

    print("\n========== 完成 ==========")
    print(f"成功: {total_ok}")
    print(f"无 SMILES: {total_no_smiles}")
    print(f"失败: {total_fail}")
    print(f"插入 compounds: {total_inserted}")

    conn.close()


if __name__ == "__main__":
    main()