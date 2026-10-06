# -*- coding: utf-8 -*-
"""方剂查询：方名 → 药材列表（对照 tcm.db）
用法：
    python formula_lookup.py 四逆汤              # 交互选版本
    python formula_lookup.py 四逆汤 --all        # 只列版本不选
    python formula_lookup.py 四逆汤 --pick 1     # 直接选第 1 个版本
"""
import sys
import re
import requests
from pathlib import Path

ROOT = Path(r"D:\TCMAI")
sys.path.insert(0, str(ROOT / "src"))

from parse_peifang import parse_peifang  # noqa: E402

API_URL = "https://cn.apihz.cn/api/jiankang/zyfj.php"
DEFAULT_ID = "88888888"
DEFAULT_KEY = "88888888"

PROCESS_PREFIX = [
    "炙", "炒", "焦", "煅", "生", "制", "炮", "熟",
    "酒", "醋", "盐", "蜜", "姜", "麸", "土", "米",
]


def fetch(words: str, page: int = 1) -> dict:
    payload = {"id": DEFAULT_ID, "key": DEFAULT_KEY, "words": words, "page": page}
    r = requests.post(API_URL, data=payload, timeout=15)
    r.raise_for_status()
    return r.json()


def normalize_herb(name: str) -> str:
    if not name:
        return name
    for p in PROCESS_PREFIX:
        if name.startswith(p) and len(name) > len(p):
            return name[len(p):]
    return name


def check_in_tcmdb(herb_names: list) -> dict:
    from db_utils import find_compounds
    result = {}
    for h in herb_names:
        for attempt in [h, normalize_herb(h)]:
            if not attempt:
                continue
            try:
                rows = find_compounds(attempt, limit=1)
            except Exception:
                rows = []
            if rows:
                result[h] = {"matched_as": attempt, "has_data": True}
                break
        else:
            result[h] = {"matched_as": None, "has_data": False}
    return result


def print_candidates(datas: list):
    print(f"共 {len(datas)} 个版本：\n")
    for i, d in enumerate(datas, 1):
        name = d.get("name") or "?"
        src = d.get("chuchu") or "?"
        peifang = (d.get("peifang") or "").strip()
        if len(peifang) > 60:
            peifang = peifang[:60] + "..."
        print(f"  [{i:2d}] {name} — {src}")
        print(f"       {peifang}")


def pick_interactive(datas: list) -> dict:
    print_candidates(datas)
    while True:
        raw = input("\n选哪个版本？(输入序号，q 退出) > ").strip()
        if raw.lower() in ("q", "quit", "exit"):
            return None
        try:
            n = int(raw)
            if 1 <= n <= len(datas):
                return datas[n - 1]
        except ValueError:
            pass
        print("无效输入，请重试。")


def analyze_version(best: dict):
    print(f"\n选中：{best.get('name')} — {best.get('chuchu')}")
    print(f"原始配方：{best.get('peifang')}\n")

    items = parse_peifang(best.get("peifang") or "")
    if not items:
        print("[空] 解析失败")
        return

    herbs = [it["herb"] for it in items]
    db_check = check_in_tcmdb(herbs)
    print(f"解析出 {len(items)} 味药：")
    for it in items:
        h = it["herb"]
        chk = db_check.get(h, {})
        flag = f"✓ {chk['matched_as']}" if chk.get("has_data") else "✗ 库中无"
        print(f"  {h:8s}  剂量={it['dose'] or '-':8s}  炮制={it['process'] or '-':12s}  {flag}")

    print(f"\n传给分析的药材名: {herbs}")


def main():
    args = sys.argv[1:]
    if not args:
        query = input("方剂名 > ").strip()
    else:
        query = args[0]

    show_all = "--all" in args
    force_pick = None
    if "--pick" in args:
        try:
            force_pick = int(args[args.index("--pick") + 1])
        except (ValueError, IndexError):
            print("[X] --pick 需要一个序号")
            return

    print(f"查询: {query}\n")
    try:
        data = fetch(query)
    except Exception as e:
        print(f"[X] 请求失败: {e}")
        return

    if data.get("code") != 200:
        print(f"[API 错误] code={data.get('code')} msg={data.get('msg')}")
        return
    datas = data.get("datas") or []
    if not datas:
        print("[空] API 返回 200 但没有 datas")
        return

    # 过滤：只保留方名完全等于查询词的（排除"茯苓四逆汤"等加味）
    exact = [d for d in datas if (d.get("name") or "").strip() == query]
    if exact:
        datas = exact

    if show_all:
        print_candidates(datas)
        return

    # 只有一条 → 直接用
    if len(datas) == 1:
        best = datas[0]
    elif force_pick is not None:
        if 1 <= force_pick <= len(datas):
            best = datas[force_pick - 1]
        else:
            print(f"[X] 序号 {force_pick} 超出范围")
            return
    else:
        best = pick_interactive(datas)
        if best is None:
            print("已取消。")
            return

    analyze_version(best)


if __name__ == "__main__":
    main()