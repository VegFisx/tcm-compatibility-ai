# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\TCMAI\src")
from admet_cache import ADMETCache

# 三个化合物的SMILES（从CAS数据库获取的标准结构）
compounds = {
    "Aconitine (乌头碱)": "CC1CCC2(C(C3(C(CC4(C(C3C(C5(C2C(C(C(C1O5)OC(=O)C)OC(=O)C6=CC=CC=C6)OC)O)OC)COC)O)C)O)OC)OC",
    "Benzoylaconine (苯甲酰乌头原碱)": "CC1CCC2(C(C3(C(CC4(C(C3C(C5(C2C(C(C(C1O5)OC(=O)C6=CC=CC=C6)OC)O)OC)COC)O)C)O)OC)OC",
    "Aconine (乌头原碱)": "CC1CCC2(C(C3(C(CC4(C(C3C(C5(C2C(C(C(C1O5)O)OC)O)OC)COC)O)C)O)OC)OC",
}

cache = ADMETCache()
print(f"ADMET 缓存: {cache.size()} 条\n")
print(f"{'化合物':30s} {'hERG预测值':>12s}")
print("-" * 45)

for name, smi in compounds.items():
    rec = cache.get(smi)
    if rec:
        herg = rec.get("hERG")
        print(f"{name:30s} {herg:>12.3f}")
    else:
        print(f"{name:30s} {'未缓存':>12s}")

cache.close()