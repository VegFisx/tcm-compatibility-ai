# -*- coding: utf-8 -*-
r"""
并排对比：原成分 vs 反应产物 的分子结构图

用法：
    python plot_compare.py 附子,甘草
    python plot_compare.py 附子,甘草 --n 4
    python plot_compare.py 甘草 --n 8
"""
import sys
import argparse
import re
from pathlib import Path
from collections import defaultdict

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(r"D:\TCMAI")
sys.path.insert(0, str(ROOT / "src"))

from rdkit import Chem, RDLogger
from rdkit.Chem import Draw, AllChem, rdMolDescriptors

RDLogger.DisableLog("rdApp.error")
RDLogger.DisableLog("rdApp.warning")

from db_utils import collect_compounds
from tcm_analyzer import predict_reactions

OUT_DIR = ROOT / "docs" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def parse_herbs(raw):
    return [h.strip() for h in re.split(r"[,，+、;；]+", raw) if h.strip()]


def mol_to_array(smiles, size=(360, 300)):
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return None
    try:
        AllChem.Compute2DCoords(m)
    except Exception:
        return None
    img = Draw.MolToImage(m, size=size)
    return np.array(img)


def collect_compounds_by_herb(herb_list, per_herb=4):
    uniq, missed = collect_compounds(herb_list, herb_limit=200,
                                     coconut_limit=1000, return_missed=True)
    by_herb = defaultdict(list)
    for c in uniq:
        h = (c.get("source") or "").replace("(COCONUT)", "")
        if len(by_herb[h]) < per_herb:
            by_herb[h].append(c)
    return by_herb, missed


def collect_products_by_rxn(herb_list, top_rxns=8):
    uniq = collect_compounds(herb_list, herb_limit=200, coconut_limit=1000)
    products = predict_reactions(uniq)
    by_rxn = {}
    for p in products:
        rxn = p.get("rxn", "?")
        if rxn not in by_rxn:
            by_rxn[rxn] = p
    return list(by_rxn.values())[:top_rxns]


def draw_grid(fig, data, x0, y0, w, h, ncols, title, title_color):
    """在归一化坐标区域画网格，data: [(smiles, label), ...]"""
    if not data:
        return
    nrows = (len(data) + ncols - 1) // ncols
    cell_w = w / ncols
    cell_h = h / max(nrows, 1)

    for i, (smi, label) in enumerate(data):
        r = i // ncols
        c = i % ncols
        cx = x0 + c * cell_w
        cy = y0 + h - (r + 1) * cell_h
        ax = fig.add_axes([cx, cy, cell_w, cell_h])
        img = mol_to_array(smi)
        if img is None:
            ax.axis("off")
            continue
        ax.imshow(img)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_edgecolor("#cccccc")
        ax.set_title(label, fontsize=8, pad=4)

    fig.text(x0 + w / 2, y0 + h + 0.015, title,
             ha="center", va="bottom", fontsize=15,
             color=title_color, weight="bold")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("herbs", help="药材名，逗号分隔")
    parser.add_argument("--n", type=int, default=4,
                        help="每味药取前 N 个原成分（默认 4）")
    parser.add_argument("--rxns", type=int, default=8,
                        help="展示前 N 种反应类型的产物（默认 8）")
    args = parser.parse_args()

    herb_list = parse_herbs(args.herbs)
    if not herb_list:
        print("请输入药材名")
        return

    print(f"药材: {herb_list}")
    print("查成分 ...")
    by_herb, missed = collect_compounds_by_herb(herb_list, per_herb=args.n)
    if missed:
        print(f"[警告] 未查到成分的药材: {missed}")

    print("跑反应 ...")
    products = collect_products_by_rxn(herb_list, top_rxns=args.rxns)
    print(f"原成分组: {len(by_herb)} 味   产物类型: {len(products)} 种")

    # 组装左侧数据（原成分）
    left_data = []
    for h, items in by_herb.items():
        for c in items:
            name = (c.get("name") or "?")[:22]
            left_data.append((c["smiles"], f"{name}\n[{h}]"))

    # 组装右侧数据（产物）
    right_data = []
    for p in products:
        rxn = p.get("rxn", "?")
        formula = p.get("formula", "")
        right_data.append((p["smiles"], f"{formula}\n{rxn}"))

    if not left_data and not right_data:
        print("没有数据，无法画图")
        return

    # 左右布局：原成分每味药独立一行区块
    # 采用统一 2 列网格
    fig = plt.figure(figsize=(16, max(9, len(left_data) * 1.1)),
                     facecolor="white")

    # 大标题
    fig.suptitle(f"{'+'.join(herb_list)}  ——  原成分 vs 反应产物",
                 fontsize=20, weight="bold", y=0.97)

    draw_grid(fig, left_data, x0=0.015, y0=0.03, w=0.47, h=0.87,
              ncols=2, title="原成分", title_color="#2980b9")
    draw_grid(fig, right_data, x0=0.515, y0=0.03, w=0.47, h=0.87,
              ncols=2, title="反应产物（RDKit 预测，无 CAS）",
              title_color="#27ae60")

    tag = "_".join(herb_list)
    out = OUT_DIR / f"fig_compare_{tag}.png"
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"\n已保存: {out}")


if __name__ == "__main__":
    main()
