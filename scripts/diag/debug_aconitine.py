# -*- coding: utf-8 -*-
"""诊断：为什么 Aconitine 的酯水解没触发"""
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem, Descriptors

RDLogger.DisableLog('rdApp.*')   # 屏蔽一堆刷屏

smi = "CCN1CC2(C(CC(C34C2C(C(C31)C5(C6C4CC(C6OC(=O)C7=CC=CC=C7)(C(C5O)OC)O)OC(=O)C)OC)OC)O)COC"
mol = Chem.MolFromSmiles(smi)
if mol is None:
    print("[ERR] SMILES 无效")
    raise SystemExit

print(f"Aconitine MW = {Descriptors.MolWt(mol):.2f}")

# 用当前规则测试
rxn = AllChem.ReactionFromSmarts(
    "[C:1](=[O:2])[O:3][C:4]>>[C:1](=[O:2])[O:3][H].[C:4][OH]"
)
res = rxn.RunReactants((mol,))
print(f"\n酯水解匹配数 = {len(res)}")

for i, prod_set in enumerate(res):
    for j, p in enumerate(prod_set):
        try:
            flag = Chem.SanitizeMol(p, catchErrors=True)
            mw = Descriptors.MolWt(p)
            ok = (flag == Chem.SanitizeFlags.SANITIZE_NONE) and mw >= 100
            print(f"  [{i}][{j}] sanitize={flag}  MW={mw:.1f}  "
                  f"{'KEEP' if ok else 'DROP'}")
            if ok:
                print(f"        SMILES: {Chem.MolToSmiles(p)[:80]}")
        except Exception as e:
            print(f"  [{i}][{j}] error: {e}")

# 试试更宽松的 SMARTS
print("\n=== 试宽松 SMARTS: [CX3:1](=[OX1:2])[OX2:3][#6:4] ===")
rxn2 = AllChem.ReactionFromSmarts(
    "[CX3:1](=[OX1:2])[OX2:3][#6:4]>>[CX3:1](=[OX1:2])[OX2:3][H].[#6:4][OH]"
)
res2 = rxn2.RunReactants((mol,))
print(f"匹配数 = {len(res2)}")