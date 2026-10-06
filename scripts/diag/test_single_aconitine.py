# -*- coding: utf-8 -*-
"""单独测试 predict_reactions 对 Aconitine 的处理"""
import sys
sys.path.insert(0, r"D:\TCMAI\src")
from tcm_analyzer import predict_reactions

ACO_SMILES = ("CCN1CC2(C(CC(C34C2C(C(C31)C5(C6C4CC(C6OC(=O)C7=CC=CC=C7)"
              "(C(C5O)OC)O)OC(=O)C)OC)OC)O)COC")

compounds = [{
    "name": "Aconitine",
    "smiles": ACO_SMILES,
    "herb_name": "附子",
}]

products = predict_reactions(compounds)
print(f"\n=== Aconitine 单独预测: {len(products)} 个产物 ===")
print("（期望 7 个：酯水解2 + 羟基氧化2 + 脱甲基2 + 脱水1）\n")
for p in sorted(products, key=lambda x: -x["mw"]):
    print(f"  {p['rxn']:8s}  MW={p['mw']:7.1f}  {p['formula']}")