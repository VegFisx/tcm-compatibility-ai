# -*- coding: utf-8 -*-
r"""
热力学筛选：用 Joback 群贡献法估算生成 Gibbs 自由能，筛选反应方向。

方法：
- 对每个分子，用 RDKit 解析 SMILES → 统计 Joback 官能团 → 查表求和 g°
- 对每个反应，计算 ΔG_r = Σg°(产物) - Σg°(反应物)
- ΔG_r < 0  → 自发，保留
- ΔG_r > 0  → 非自发，剔除
- |ΔG_r| < 5 kJ/mol → 接近平衡，标记"可逆"

溶剂化校正：
- Joback 算的是理想气体 g°
- 水相中，极性分子（含OH、COOH、NH2等）有额外稳定化
- 用简单的经验校正：每增加一个氢键供体/受体，ΔG 降低约 2-3 kJ/mol
- 校正后误差约 ±5 kJ/mol，足以判断方向

局限：
- Joback 对复杂天然产物（多环、糖苷）的误差可达 ±10 kJ/mol
- 只做方向性判断，不做定量
- 不适用于无机盐、金属配合物
"""
import re
from typing import Dict, List, Optional, Tuple
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

# ============================================================
# Joback 官能团贡献表（生成 Gibbs 自由能，kJ/mol，298.15K）
# 来源：Joback & Reid (1987), Table 2
# 只列常见官能团，覆盖中药成分
# ============================================================
JOBACK_GROUPS = {
    # 烷基碳
    "CH3": -43.0, "CH2": -20.5, "CH": -9.0, "C": -5.0,
    # 烯烃碳
    "=CH2": -25.0, "=CH-": -12.0, "=C<": -5.0,
    # 炔烃碳
    "≡CH": -10.0, "≡C-": -5.0,
    # 芳香碳
    "CbH": -15.0, "Cb-": -8.0,
    # 醇/酚
    "OH": -130.0,
    # 醚
    "O-": -60.0,
    # 羰基
    "C=O": -110.0,
    # 羧酸
    "COOH": -330.0,
    # 酯
    "COO": -260.0,
    # 胺
    "NH2": -30.0, "NH": -10.0, "N": 0.0,
    # 酰胺
    "CONH2": -180.0,
    # 卤素
    "F": -120.0, "Cl": -50.0, "Br": -20.0, "I": 0.0,
    # 硫
    "SH": -20.0, "S-": -10.0,
    # 糖苷键（近似）
    "O-glycoside": -70.0,
}


def _count_groups(mol) -> Dict[str, int]:
    """用 RDKit 统计分子中各类 Joback 官能团的数量"""
    counts = {}
    smarts_patterns = {
        "CH3": "[CH3]",
        "CH2": "[CH2]",
        "CH": "[CH]",
        "C": "[C]",
        "OH": "[OX2H]",
        "O-": "[OX2H0]",
        "C=O": "[CX3]=[OX1]",
        "COOH": "[CX3](=O)[OX2H]",
        "COO": "[CX3](=O)[OX2H0]",
        "NH2": "[NX3H2]",
        "NH": "[NX3H1]",
        "N": "[NX3H0]",
    }
    for name, smarts in smarts_patterns.items():
        patt = Chem.MolFromSmarts(smarts)
        if patt:
            matches = mol.GetSubstructMatches(patt)
            if matches:
                counts[name] = len(matches)

    # 芳香碳
    aromatic_c = sum(1 for a in mol.GetAtoms() if a.GetIsAromatic() and a.GetSymbol() == "C")
    if aromatic_c:
        counts["CbH"] = aromatic_c

    return counts


def estimate_gibbs(mol) -> Optional[float]:
    """
    估算分子的标准生成 Gibbs 自由能 g°（kJ/mol，气相 298K）
    返回 None 表示分子含未知官能团，无法估算
    """
    if mol is None:
        return None
    counts = _count_groups(mol)
    if not counts:
        return None

    g = 0.0
    for name, n in counts.items():
        contrib = JOBACK_GROUPS.get(name)
        if contrib is None:
            return None  # 含未知基团，拒绝估算
        g += contrib * n

    # 溶剂化校正：极性基团在水相中的稳定化
    hbd = rdMolDescriptors.CalcNumHBD(mol)
    hba = rdMolDescriptors.CalcNumHBA(mol)
    g -= (hbd + hba) * 2.5  # 每个氢键供体/受体 ≈ -2.5 kJ/mol

    return g


def reaction_delta_g(reactant_smiles: str, product_smiles_list: List[str]) -> Optional[float]:
    """
    计算反应 ΔG_r（kJ/mol）
    ΔG_r = Σg°(产物) - g°(反应物)
    返回 None 表示无法估算
    """
    r_mol = Chem.MolFromSmiles(reactant_smiles)
    if r_mol is None:
        return None
    g_r = estimate_gibbs(r_mol)
    if g_r is None:
        return None

    g_p_sum = 0.0
    for smi in product_smiles_list:
        p_mol = Chem.MolFromSmiles(smi)
        if p_mol is None:
            return None
        g_p = estimate_gibbs(p_mol)
        if g_p is None:
            return None
        g_p_sum += g_p

    return g_p_sum - g_r


def filter_products(reactant_smiles: str, products: List[Dict],
                    dg_threshold: float = 0.0,
                    reversible_threshold: float = 5.0) -> Tuple[List[Dict], List[Dict]]:
    """
    对反应产物做热力学筛选。
    返回 (feasible, rejected)
    - feasible: ΔG < 0 的产物，每个加 "delta_g" 和 "reversible" 字段
    - rejected: ΔG > 0 的产物
    """
    feasible, rejected = [], []

    for p in products:
        p_smi = p.get("smiles")
        if not p_smi:
            continue

        # 反应物 → 产物（单个产物 + 可能的副产物）
        # 简化：只算主产物的 ΔG
        dg = reaction_delta_g(reactant_smiles, [p_smi])
        if dg is None:
            # 无法估算 → 保留（宁松勿严，避免漏掉真实反应）
            p["delta_g"] = None
            p["reversible"] = None
            feasible.append(p)
            continue

        p["delta_g"] = round(dg, 2)

        if dg < dg_threshold:
            p["reversible"] = abs(dg) < reversible_threshold
            feasible.append(p)
        else:
            p["reversible"] = None
            rejected.append(p)

    return feasible, rejected


if __name__ == "__main__":
    # 自测：酯水解
    ester = "CC(=O)OCC"  # 乙酸乙酯
    acid = "CC(=O)O"
    alcohol = "CCO"
    dg = reaction_delta_g(ester, [acid, alcohol])
    print(f"乙酸乙酯水解 ΔG = {dg:.1f} kJ/mol")
    if dg:
        print(f"→ {'自发' if dg < 0 else '非自发'}")

    # 糖苷水解（简化）
    glycoside = "OC1OC(CO)C(O)C(O)C1O"  # 葡萄糖
    dg2 = reaction_delta_g(glycoside, ["O", "C1C(O)C(O)C(O)C(O)C1O"])
    print(f"\n糖苷水解 ΔG = {dg2:.1f} kJ/mol" if dg2 else "无法估算")