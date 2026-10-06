# -*- coding: utf-8 -*-
"""测试 apihz 中医方剂 API
用法：
    python test_formula_api.py 四逆汤
    python test_formula_api.py 四逆汤 --id 你的ID --key 你的KEY
"""
import sys
import json
import requests
from pathlib import Path

API_URL = "https://cn.apihz.cn/api/jiankang/zyfj.php"
# 公共测试 ID/KEY（共享频率限制），正式使用请替换为自己的
DEFAULT_ID = "88888888"
DEFAULT_KEY = "88888888"


def query_formula(words: str, dev_id: str = DEFAULT_ID, dev_key: str = DEFAULT_KEY,
                  page: int = 1) -> dict:
    """查询方剂，返回 API 原始 JSON"""
    payload = {
        "id": dev_id,
        "key": dev_key,
        "words": words,
        "page": page,
    }
    resp = requests.post(API_URL, data=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def main():
    args = sys.argv[1:]
    if not args:
        words = input("输入方剂名/症状/药材名 > ").strip()
    else:
        words = args[0]

    dev_id, dev_key = DEFAULT_ID, DEFAULT_KEY
    if "--id" in args:
        dev_id = args[args.index("--id") + 1]
    if "--key" in args:
        dev_key = args[args.index("--key") + 1]

    print(f"查询: {words}  (id={dev_id})")
    try:
        data = query_formula(words, dev_id, dev_key)
    except Exception as e:
        print(f"[X] 请求失败: {e}")
        sys.exit(1)

    print(f"code = {data.get('code')}  msg = {data.get('msg')}")
    datas = data.get("datas")
    if not datas:
        print("[空] 没有匹配结果")
        return

    for i, item in enumerate(datas, 1):
        print(f"\n--- [{i}] {item.get('name')} ---")
        print(f"  配方: {item.get('peifang')}")
        print(f"  出处: {item.get('chuchu')}")
        print(f"  功效: {item.get('gongxiao')}")
        print(f"  用法: {item.get('yongfa')}")


if __name__ == "__main__":
    main()