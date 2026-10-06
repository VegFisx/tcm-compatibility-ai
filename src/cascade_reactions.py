# -*- coding: utf-8 -*-
r"""
迭代反应至稳定态（反应可达闭包）—— v3
只对"不可逆"反应的产物继续迭代；可逆反应只做单步预测，不递归。

理由：
- 煎煮条件下，水解、脱羧、氧化等不可逆反应会持续到底物耗尽
- 酯化、烯醇化、水合等可逆反应很快达平衡，不产生新分子
- 只迭代不可逆方向，级联才能真实收敛

返回结构：
{
  "products": [...],          # 所有产物（含各轮）
  "total": N,
  "rounds": R,
  "round_stats": [{round, new, irreversible_new}],
  "converged": bool,
}
"""
from collections import defaultdict
from typing import Dict, List

from tcm_analyzer import predict_reactions, get_reactions


def _irreversible_rules() -> set:
    """返回所有 irreversible=True 的规则名集合"""
    rxn = get_reactions()
    return {name for name, info in rxn.items()
            if info.get("irreversible", False)}


def find_final_products(compounds: List[Dict],
                        max_rounds: int = 10,
                        frontier_limit: int = 500,
                        min_new: int = 10) -> Dict:
    """
    compounds: 原成分列表
    max_rounds: 最多迭代几轮
    frontier_limit: 每轮作为下一轮底物的最大分子数
    min_new: 单轮"不可逆新增" < min_new 视为收敛

    返回：终态产物池 + 统计信息
    """
    irr_rules = _irreversible_rules()

    frontier = list(compounds)
    all_smiles = {c["smiles"] for c in compounds if c.get("smiles")}
    all_products: Dict[str, Dict] = {}
    by_round: Dict[int, List[Dict]] = defaultdict(list)
    round_stats = []

    for r in range(max_rounds):
        if not frontier:
            break

        raw = predict_reactions(frontier)

        all_new = []
        irrev_new = []
        for p in raw:
            smi = p.get("smiles")
            if not smi or smi in all_smiles:
                continue
            all_smiles.add(smi)
            rec = {
                "smiles": smi,
                "formula": p.get("formula"),
                "mw": p.get("mw"),
                "rxn": p.get("rxn"),
                "from_compound": p.get("from_compound"),
                "from_herb": p.get("from_herb"),
                "round": r + 1,
                "irreversible": p.get("rxn") in irr_rules,
            }
            all_products[smi] = rec
            by_round[r + 1].append(rec)
            all_new.append(p)
            if rec["irreversible"]:
                irrev_new.append(p)

        round_stats.append({
            "round": r + 1,
            "new": len(all_new),
            "irreversible_new": len(irrev_new),
        })

        # 收敛：不可逆新增 < min_new（可逆反应不驱动体系继续）
        if len(irrev_new) < min_new:
            break

        # 下一轮底物：只取"不可逆"产物，按反应类型均衡采样
        if len(irrev_new) > frontier_limit:
            by_rxn = defaultdict(list)
            for p in irrev_new:
                by_rxn[p.get("rxn", "?")].append(p)
            n_types = max(1, len(by_rxn))
            per_type = max(1, frontier_limit // n_types)
            sampled = []
            for rxn, items in by_rxn.items():
                sampled.extend(items[:per_type])
            sampled = sampled[:frontier_limit]
        else:
            sampled = irrev_new

        frontier = [
            {
                "smiles": p["smiles"],
                "name": f"R{r+2} 底物",
                "source": "cascade",
                "herb_name": "cascade",
            }
            for p in sampled
        ]

    converged = bool(round_stats) and round_stats[-1]["irreversible_new"] < min_new

    return {
        "products": list(all_products.values()),
        "total": len(all_products),
        "rounds": len(round_stats),
        "round_stats": round_stats,
        "converged": converged,
        "by_round": dict(by_round),
    }


if __name__ == "__main__":
    import sys
    from pathlib import Path
    ROOT = Path(r"D:\TCMAI")
    sys.path.insert(0, str(ROOT / "src"))
    from db_utils import find_compounds

    rows = find_compounds("甘草", limit=30)
    print(f"原成分: {len(rows)}")
    result = find_final_products(rows, max_rounds=10, frontier_limit=200)
    print(f"收敛: {result['converged']}")
    print(f"跑了 {result['rounds']} 轮")
    for s in result["round_stats"]:
        print(f"  第 {s['round']} 轮: 总新增 {s['new']}, "
              f"不可逆 {s['irreversible_new']}")
    print(f"终态产物总数: {result['total']}")