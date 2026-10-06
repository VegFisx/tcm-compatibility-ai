# -*- coding: utf-8 -*-
r"""
剂量加权：把方剂里的剂量字符串转成相对权重。

设计原则：
- 不追求绝对克数（历代度量衡差异大），只求"同一方内各药相对投入量"
- 基准：1 钱 = 1 分单位；1 两 = 10；1 斤 = 160；1 枚 ≈ 10
- 支持 重量 / 计数 / 容量 三类单位
- 方内归一化，总和=1

局限：
- 同一味药内各成分按等权处理（无含量数据）
- 单位换算为经验值，不反映历代度量衡差异
"""
import re
from typing import Dict, List, Optional

# 单位 → 相对分（1 钱 = 1 分）
UNIT_SCORES = {
    # 重量
    "斤": 160, "两": 10, "钱": 1, "分": 0.1, "厘": 0.01,
    "克": 0.32, "g": 0.32, "G": 0.32,
    # 计数（粗略）
    "枚": 10, "个": 10, "片": 2, "条": 10, "寸": 5,
    "粒": 1, "只": 10, "把": 20, "束": 20, "团": 20, "撮": 5,
    # 容量
    "升": 100, "合": 10, "盏": 50, "杯": 50, "碗": 100,
}

CN_DIGITS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
             "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
             "半": 0.5}


def _parse_number(s: str) -> float:
    """'2'→2.0; '一'→1.0; '十'→10.0; '十二'→12.0; '半'→0.5"""
    if not s:
        return 0.0
    s = s.strip()
    try:
        return float(s)
    except ValueError:
        pass
    if s in CN_DIGITS:
        return float(CN_DIGITS[s])
    if "十" in s:
        parts = s.split("十")
        tens = CN_DIGITS.get(parts[0], 1) if parts[0] else 1
        units = CN_DIGITS.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
        return tens * 10 + units
    return 0.0


def parse_amount(s: Optional[str]) -> float:
    """'2两'→20.0; '1两半'→15.0; '半两'→5.0; '3钱'→3.0; '1枚'→10.0"""
    if not s:
        return 0.0
    s = s.strip()

    # 找单位（长单位优先）
    unit = None
    for u in sorted(UNIT_SCORES, key=len, reverse=True):
        if u in s:
            unit = u
            break
    if not unit:
        return 0.0

    score = UNIT_SCORES[unit]
    idx = s.index(unit)
    num_str = s[:idx]
    tail = s[idx + len(unit):]

    n = _parse_number(num_str) if num_str else 1.0
    if "半" in tail:
        n += 0.5
    return n * score


def compute_weights(items: List[Dict]) -> Dict[str, float]:
    """
    items: parse_peifang 的输出 [{"herb":..., "dose":...}, ...]
    返回 {herb_name: weight}，权重归一化到总和=1。
    - 全无剂量 → 等权
    - 部分有剂量 → 有剂量的按比例，无剂量的取最小非零权重的 1/2
    """
    scores: Dict[str, float] = {}
    for it in items:
        h = it.get("herb")
        if not h:
            continue
        scores[h] = scores.get(h, 0.0) + parse_amount(it.get("dose"))

    if not scores:
        return {}

    non_zero = [v for v in scores.values() if v > 0]
    if not non_zero:
        n = len(scores)
        return {h: 1.0 / n for h in scores}

    fallback = min(non_zero) / 2
    for h in scores:
        if scores[h] == 0:
            scores[h] = fallback

    total = sum(scores.values())
    return {h: v / total for h, v in scores.items()}


if __name__ == "__main__":
    # 自测
    cases = ["甘草2两（炙），干姜1两半，附子1枚（生用，去皮，破8片）。",
             "炙甘草、熟附子、干姜、葱白。"]
    from parse_peifang import parse_peifang
    for c in cases:
        items = parse_peifang(c)
        w = compute_weights(items)
        print(f"\n{c}")
        for h, wv in w.items():
            print(f"  {h:8s} {wv:.3f}")