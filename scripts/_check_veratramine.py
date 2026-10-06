# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\TCMAI\src")
from db_utils import collect_compounds
from tcm_analyzer import check_toxicity

for herbs in [["八角茴香", "甘草"], ["大茴香", "甘草"]]:
    print(f"\n=== {herbs} ===")
    uniq, missed = collect_compounds(herbs, return_missed=True)
    print(f"成分 {len(uniq)}, 未命中: {missed}")
    tox = [c for c in uniq if check_toxicity(c)]
    print(f"毒性分子 {len(tox)} 个:")
    for c in tox[:10]:
        src = c.get("source") or c.get("herb_name") or "?"
        print(f"  {c.get('name'):40s}  来源: {src}")