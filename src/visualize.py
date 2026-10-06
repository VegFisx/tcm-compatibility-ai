# -*- coding: utf-8 -*-
"""
分子结构可视化模块
- 画单个分子
- 网格画多个分子（毒性清单 / 配伍对比）
- 画反应路径（反应物 → 产物）
- 支持从 tcm.db / coconut.db 自动抽毒性分子

用法示例见文件末尾 __main__
"""
import os
import sqlite3
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from rdkit import Chem
from rdkit.Chem import Draw, AllChem


# ============================================================
# 基础工具
# ============================================================
def _to_mol(smiles: str):
    """SMILES → RDKit Mol（自动算 2D 坐标）"""
    if not smiles or not isinstance(smiles, str):
        return None
    mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None:
        return None
    AllChem.Compute2DCoords(mol)
    return mol


def _ensure_dir(path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)


# ============================================================
# 1. 单分子
# ============================================================
def draw_molecule(
    smiles: str,
    output_path: str,
    legend: str = "",
    size: Tuple[int, int] = (400, 400),
) -> bool:
    mol = _to_mol(smiles)
    if mol is None:
        print(f"[skip] invalid SMILES: {str(smiles)[:60]}")
        return False
    img = Draw.MolToImage(mol, size=size, legend=legend)
    _ensure_dir(output_path)
    img.save(output_path)
    print(f"[ok] {output_path}")
    return True


# ============================================================
# 2. 网格图（最常用）
# ============================================================
def draw_grid(
    entries: Sequence[Tuple[str, str]],
    output_path: str,
    mols_per_row: int = 4,
    size: Tuple[int, int] = (320, 320),
) -> bool:
    """
    entries: [(smiles, legend), ...]
    """
    mols, legends = [], []
    for smi, leg in entries:
        m = _to_mol(smi)
        if m is None:
            continue
        mols.append(m)
        legends.append(leg)
    if not mols:
        print("[warn] 没有可绘制的分子")
        return False

    img = Draw.MolsToGridImage(
        mols,
        molsPerRow=mols_per_row,
        subImgSize=size,
        legends=legends,
    )
    _ensure_dir(output_path)
    img.save(output_path)
    print(f"[ok] {len(mols)} 个分子 → {output_path}")
    return True


# ============================================================
# 3. 反应路径（反应物 → 产物）
# ============================================================
def draw_reaction_path(
    reactant_smiles: str,
    products: Sequence[Tuple[str, str]],
    output_path: str,
    reactant_label: str = "Reactant",
    size: Tuple[int, int] = (320, 320),
) -> bool:
    """
    products: [(smiles, label), ...]
    布局: 反应物 在左, 产物依次排开
    """
    entries = [(reactant_smiles, reactant_label)] + list(products)
    per_row = min(4, len(entries)) if len(entries) > 1 else 1
    return draw_grid(entries, output_path, mols_per_row=per_row, size=size)


# ============================================================
# 4. 从数据库抽分子（自动过滤无 SMILES）
# ============================================================
def fetch_smiles_by_keyword(
    db_path: str,
    table: str,
    name_col: str,
    smiles_col: str,
    keywords: Sequence[str],
    limit_per_kw: int = 3,
) -> List[Tuple[str, str]]:
    """
    从数据库按关键词抓成分
    返回 [(name, smiles), ...]
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    out: List[Tuple[str, str]] = []
    seen = set()
    for kw in keywords:
        try:
            cur.execute(
                f"""SELECT DISTINCT {name_col}, {smiles_col}
                    FROM {table}
                    WHERE {name_col} LIKE ?
                      AND {smiles_col} IS NOT NULL
                      AND {smiles_col} != ''
                    LIMIT ?""",
                (f"%{kw}%", limit_per_kw),
            )
            for name, smi in cur.fetchall():
                if smi in seen:
                    continue
                seen.add(smi)
                out.append((name or kw, smi))
        except sqlite3.Error as e:
            print(f"[db warn] {kw}: {e}")
    conn.close()
    return out


# ============================================================
# 5. 与 analyzer 对接的高阶封装
# ============================================================
def draw_toxic_report(
    toxic_compounds: Sequence[Tuple[str, str, str]],
    output_path: str,
    title: str = "Toxic Compounds",
    mols_per_row: int = 4,
) -> bool:
    """
    toxic_compounds: [(name, smiles, source), ...]
    """
    entries = [(smi, f"{name}\n[{src}]") for name, smi, src in toxic_compounds if smi]
    if not entries:
        print(f"[warn] {title}: 无毒分子可画")
        return False
    print(f"\n=== {title} ===")
    return draw_grid(entries, output_path, mols_per_row=mols_per_row)


# ============================================================
# Demo
# ============================================================
if __name__ == "__main__":
    ROOT = Path(r"D:\TCMAI")
    OUT = ROOT / "docs" / "figures"
    OUT.mkdir(parents=True, exist_ok=True)

    # 1) 用已知 SMILES 画一个 demo
    demo = [
        ("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "Caffeine"),
        ("C1=CC(=CC=C1C=CC2=CC(=C(C=C2)O)O)O", "Resveratrol"),
        ("COc1ccc(cc1)C=CC(=O)CC(=O)C=Cc1ccc(O)c(OC)c1", "Curcumin"),
    ]
    draw_grid(demo, str(OUT / "demo_grid.png"), mols_per_row=3)

    # 2) 从 tcm.db 抓甘草/附子毒性分子
    tcm_db = str(ROOT / "tcm.db")
    if os.path.exists(tcm_db):
        print("\n--- 从 tcm.db 抓毒性分子 ---")
        keywords = ["乌头碱", "次乌头碱", "新乌头碱", "甘草酸", "甘草苷"]
        hits = fetch_smiles_by_keyword(
            tcm_db, "compounds", "name", "smiles", keywords, limit_per_kw=2
        )
        entries = [(smi, name) for name, smi in hits]
        if entries:
            draw_grid(entries, str(OUT / "tcm_toxic_demo.png"), mols_per_row=4)

    print("\n[done] 图保存在:", OUT)