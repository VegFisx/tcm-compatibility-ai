# -*- coding: utf-8 -*-
r"""
验证剩余 3 条 0 命中的规则
- 醌还原：用丹参（丹参酮含醌）
- 硫酸酯水解：用海藻（硫酸多糖）
- 芳香酸脱羧：用大黄（含蒽醌羧酸）
"""
import sys
from pathlib import Path

ROOT = Path(r"D:\TCMAI")
sys.path.insert(0, str(ROOT / "src"))

from db_utils import find_compounds
from tcm_analyzer import predict_reactions, REACTIONS, _LAST_RXN_STATS

# 测试用药（含特定结构）
TEST_HERBS = {
    "丹参": {  # 丹参酮含醌
        "include": ["丹参"],
        "coconut": ["salvia miltiorrhiza"],
    },
    "海藻": {  # 硫酸多糖
        "include": ["海藻"],
        "coconut": ["sargassum pallidum", "sargassum fusiforme"],
    },
    "大黄": {  # 蒽醌羧酸
        "include": ["大黄", "酒大黄", "熟大黄"],
        "coconut": ["rheum palmatum", "rheum officinale", "rheum tanguticum"],
    },
}

print("=" * 70)
print("规则验证")
print("=" * 70)

from db_utils import find_compounds_coconut

for herb, cfg in TEST_HERBS.items():
    print(f"\n=== {herb} ===")
    compounds = []

    # HERB
    herb_rows = find_compounds(herb, include=cfg["include"], limit=200)
    for r in herb_rows:
        r["source"] = herb
        compounds.append(r)
    print(f"  HERB: {len(herb_rows)} 成分")

    # COCONUT
    if cfg.get("coconut"):
        coco_rows = find_compounds_coconut(cfg["coconut"], limit=1000)
        for r in coco_rows:
            r["source"] = f"{herb}(COCONUT)"
            compounds.append(r)
        print(f"  COCONUT: {len(coco_rows)} 成分")

    # 去重
    seen, uniq = set(), []
    for c in compounds:
        smi = c.get("smiles")
        if not smi or smi in seen:
            continue
        seen.add(smi)
        uniq.append(c)

    # 只跑反应，看统计
    products = predict_reactions(uniq)
    print(f"  产物: {len(products)}")
    print(f"  规则命中:")
    for name, count in sorted(_LAST_RXN_STATS.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"    {name:16s} : {count}")