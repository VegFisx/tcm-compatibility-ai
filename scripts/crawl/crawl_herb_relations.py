# D:\TCMAI\scripts\crawl\crawl_herb_relations.py
import os
import re
import time
import random
import sqlite3
import argparse
from datetime import datetime

import requests

# ==================== 配置 ====================
DB = r"D:\TCMAI\tcm.db"          # 数据库路径
API = "http://herb.ac.cn/chedi/api/"
# ==============================================

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "http://herb.ac.cn",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/152.0.0.0 Safari/537.36 Edg/152.0.0.0",
}

HBIN_RE = re.compile(r"HBIN\d{6,}")


def now():
    return datetime.now().isoformat(timespec="seconds")


def get_conn():
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db(conn):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS crawl_progress (
        herb_id TEXT PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'pending',
        http_status INTEGER,
        n_compounds INTEGER DEFAULT 0,
        error TEXT,
        updated_at TEXT
    )
    """)
    # 确保 herb_compound 有唯一约束
    try:
        conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_herb_compound_unique
        ON herb_compound(herb_id, ingredient_id)
        """)
    except sqlite3.OperationalError as e:
        print("创建唯一索引失败（可能已有重复数据）：", e)
    conn.commit()


def get_tasks(conn, limit=None, force=False):
    if force:
        where = "1=1"
    else:
        where = "p.status IS NULL OR p.status IN ('pending', 'failed')"
    sql = f"""
    SELECT h.herb_id
    FROM herbs h
    LEFT JOIN crawl_progress p ON p.herb_id = h.herb_id
    WHERE {where}
    ORDER BY h.herb_id
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    return [row[0] for row in conn.execute(sql).fetchall()]


def fetch_herb(herb_id):
    """调用 HERB API，返回 JSON dict"""
    payload = {
        "v": herb_id,
        "label": "Herb",
        "key_id": herb_id,
        "func_name": "detail_api",
    }
    headers = dict(HEADERS)
    headers["Referer"] = f"http://herb.ac.cn/Detail/?v={herb_id}&label=Herb"

    r = requests.post(API, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    return r.json(), r.status_code


def extract_hbins(data):
    """从返回 JSON 的 herb_ingredient 字段里提取 HBIN"""
    import json
    section = data.get("herb_ingredient") or []
    text = json.dumps(section, ensure_ascii=False)
    return sorted(set(HBIN_RE.findall(text)))


def save_success(conn, herb_id, hbins, http_status):
    for hbin in hbins:
        conn.execute("""
        INSERT OR IGNORE INTO herb_compound
        (herb_id, ingredient_id, match_level, match_source)
        VALUES (?, ?, ?, ?)
        """, (herb_id, hbin, "herb_online", "HERB_detail"))

    conn.execute("""
    INSERT OR REPLACE INTO crawl_progress
    (herb_id, status, http_status, n_compounds, error, updated_at)
    VALUES (?, 'done', ?, ?, NULL, ?)
    """, (herb_id, http_status, len(hbins), now()))
    conn.commit()


def save_failed(conn, herb_id, err, http_status=None):
    conn.execute("""
    INSERT OR REPLACE INTO crawl_progress
    (herb_id, status, http_status, n_compounds, error, updated_at)
    VALUES (?, 'failed', ?, 0, ?, ?)
    """, (herb_id, http_status, str(err)[:500], now()))
    conn.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="只爬前 N 个，测试用")
    parser.add_argument("--force", action="store_true", help="忽略进度，全部重爬")
    parser.add_argument("--start", type=str, default=None, help="从指定 herb_id 开始")
    args = parser.parse_args()

    conn = get_conn()
    init_db(conn)
    tasks = get_tasks(conn, limit=args.limit, force=args.force)

    if args.start:
        tasks = [t for t in tasks if t >= args.start]

    print(f"待爬药材数：{len(tasks)}")

    total_hbins = 0
    empty_count = 0
    fail_count = 0

    for i, herb_id in enumerate(tasks, 1):
        try:
            data, status = fetch_herb(herb_id)
            hbins = extract_hbins(data)
            save_success(conn, herb_id, hbins, status)
            total_hbins += len(hbins)
            if not hbins:
                empty_count += 1
            print(f"[{i}/{len(tasks)}] {herb_id} -> {len(hbins)} 个成分 "
                  f"| 累计 {total_hbins} | 空 {empty_count} | 失败 {fail_count}")
        except Exception as e:
            fail_count += 1
            save_failed(conn, herb_id, e)
            print(f"[{i}/{len(tasks)}] {herb_id} 失败：{e}")

        # 频率控制：1.2 ~ 2.0 秒
        time.sleep(random.uniform(1.2, 2.0))

    print("\n========== 完成 ==========")
    print(f"总药材：{len(tasks)}")
    print(f"总成分关系：{total_hbins}")
    print(f"空结果药材：{empty_count}")
    print(f"失败药材：{fail_count}")

    conn.close()


if __name__ == "__main__":
    main()